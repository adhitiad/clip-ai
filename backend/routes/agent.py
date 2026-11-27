"""Agent short-form: brief kreatif + opsional antre render video 9:16."""

import asyncio
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.agent import build_few_shot_prompt_context, plan_shorts
from backend.core.auth import get_current_active_user, get_db
from backend.core.rate_limit import check_rate_limit
from backend.core.request_id import get_request_id
from backend.core.telemetry import current_traceparent
from backend.log import logger
from backend.models.user import User
from backend.services.video_discovery import discover_videos_for_topic

router = APIRouter(prefix="/agent", tags=["Shorts Agent"])


class Platform(str, Enum):
    shorts = "shorts"
    reels = "reels"
    tiktok = "tiktok"


class ShortsRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    video_url: str | None = Field(
        default=None, description="Satu video sumber (kompatibel lama)"
    )
    video_urls: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Beberapa video sumber; minimal 2 untuk mix",
    )
    platform: Platform = Platform.shorts
    target_language: str = "id"
    max_clips: int = Field(default=3, ge=1, le=5)
    render_video: bool = False
    mix_sources: bool = Field(
        default=True, description="Gabung klip dari beberapa sumber jadi satu MP4"
    )
    min_source_seconds: int = Field(
        default=240,
        ge=0,
        le=7200,
        description="Durasi minimum tiap video sumber (default 4 menit)",
    )
    auto_discover: bool = Field(
        default=True,
        description="Otomatis cari video dari topik bila tidak ada video_url/video_urls",
    )
    provider: str | None = Field(
        default=None, description="Kosong → AGENT_PROVIDER/discovery"
    )
    model: str | None = Field(default=None, description="Kosong → AGENT_MODEL/katalog")


def _request_sources(request: ShortsRequest) -> list[str]:
    """Gabungkan video_url + video_urls, buang duplikat/kosong, jaga urutan."""
    candidates = ([request.video_url] if request.video_url else []) + list(
        request.video_urls
    )
    sources: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        url = (candidate or "").strip()
        if url and url not in seen:
            seen.add(url)
            sources.append(url)
    return sources


def _select_mixed_clips(per_source: list[list[dict]], max_clips: int) -> list[dict]:
    """Ambil klip bergiliran dari tiap sumber, skor tertinggi dulu."""
    ranked = [
        sorted(group, key=lambda clip: int(clip.get("viral_score", 0)), reverse=True)
        for group in per_source
    ]
    selected: list[dict] = []
    depth = 0
    while len(selected) < max_clips:
        added = False
        for group in ranked:
            if depth >= len(group):
                continue
            selected.append(group[depth])
            added = True
            if len(selected) == max_clips:
                break
        if not added:
            break
        depth += 1
    return selected


def _few_shot(topic: str) -> str:
    try:
        return build_few_shot_prompt_context(topic)
    except Exception as exc:
        logger.warning(f"[Agent] Few-shot tidak tersedia: {exc}")
        return "Belum ada contoh masa lalu."


def _apply_plan_to_clips(clips: list[dict], plan, target_language: str) -> list[dict]:
    """Gabungkan timing asli dari AI pipeline dengan copy dari agent."""
    for index, clip in enumerate(clips):
        if index >= len(plan.clips):
            break
        planned = plan.clips[index]
        title = planned.title
        desc = f"{planned.hook} {planned.caption}".strip()
        if planned.hashtags:
            desc += " " + " ".join(planned.hashtags)
        clip["title_id"] = title
        clip["title_en"] = title
        clip["desc_id"] = desc
        clip["desc_en"] = desc
        clip["hook"] = planned.hook
        clip["agent_hashtags"] = planned.hashtags
        clip["target_language"] = target_language
        clip["thumbnail_path"] = clip.get("thumbnail_path")
        clip["thumbnail_url"] = clip.get("thumbnail_url")
    return clips


def _plan_shorts_sync(request: ShortsRequest):
    try:
        return plan_shorts(
            topic=request.topic,
            platform=request.platform.value,
            max_clips=request.max_clips,
            target_language=request.target_language,
            few_shot=_few_shot(request.topic),
            provider=request.provider,
            model=request.model,
        )
    except Exception as exc:
        logger.error(f"[Agent] Gagal menyusun rencana: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provider LLM agent belum siap. Cek AGENT_PROVIDER/AGENT_MODEL di .env.",
        ) from exc


def _build_clips_sync(request: ShortsRequest) -> list[dict]:
    import os

    from backend.core.ai_pipeline import process_video_ai_logic
    from backend.utils.youtube import (
        check_and_get_youtube_subs,
        download_audio_only,
        get_video_info,
    )

    sources = _request_sources(request)
    if not sources and request.auto_discover:
        try:
            discovered = discover_videos_for_topic(
                topic=request.topic,
                niche=None,
                max_videos=request.max_clips + 2,
                min_duration_seconds=request.min_source_seconds,
                ai_select=True,
            )
        except Exception as exc:
            logger.warning(f"[VideoDiscovery] Auto-discover gagal: {exc}")
            discovered = []
        sources = [item["url"] for item in discovered if item.get("url")]
        if not sources:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Tidak ditemukan video sumber yang cocok dengan topik. "
                    "Berikan video_url/video_urls secara manual."
                ),
            )

    per_source: list[list[dict]] = []
    skipped: list[str] = []

    for source_index, video_url in enumerate(sources):
        info = get_video_info(video_url) if request.min_source_seconds else {}
        duration = info.get("duration")
        if (
            request.min_source_seconds
            and isinstance(duration, (int, float))
            and duration < request.min_source_seconds
        ):
            logger.warning(
                "[Agent] Sumber terlalu pendek "
                f"({duration}s < {request.min_source_seconds}s): {video_url}"
            )
            skipped.append(video_url)
            continue

        transcript = (
            check_and_get_youtube_subs(video_url, request.target_language) or ""
        )
        audio_path = "" if transcript else download_audio_only(video_url)
        try:
            clips = process_video_ai_logic(
                audio_path=audio_path,
                user_query=request.topic,
                transcript_text=transcript,
            )
        except Exception as exc:
            logger.warning(
                f"[Agent] Gagal analisis sumber {video_url}: {type(exc).__name__}"
            )
            clips = []
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

        for clip in clips:
            clip["source_url"] = video_url
            clip["source_index"] = source_index
            clip["source_title"] = info.get("title", "")
        per_source.append(clips)

    selected = _select_mixed_clips(per_source, request.max_clips)
    if request.mix_sources and len(sources) > 1:
        used = {clip.get("source_url") for clip in selected}
        if len(used) < 2:
            detail = "Minimal 2 video sumber harus menghasilkan klip untuk mix."
            if skipped:
                detail += " Sumber terlalu pendek: " + ", ".join(skipped)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
            )
    return selected


@router.post("/shorts")
async def create_shorts(
    request: ShortsRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Rencanakan short/reel/tiktok (brief JSON). Jika ``render_video=true``,
    pipeline video existing dipakai dan task render diantre ke Taskiq.
    Beberapa ``video_urls`` digabung jadi satu MP4 (``mix_sources``).
    """
    try:
        check_rate_limit("agent")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None

    sources = _request_sources(request)
    if request.render_video and not sources and not request.auto_discover:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="video_url atau video_urls wajib diisi saat render_video=true.",
        )
    if len(sources) > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Maksimal 5 video sumber per permintaan.",
        )
    mix_sources = request.mix_sources and len(sources) > 1

    plan = await asyncio.to_thread(_plan_shorts_sync, request)

    brief = plan.as_dict()
    if not request.render_video:
        return {"status": "brief", "brief": brief}

    clips = await asyncio.to_thread(_build_clips_sync, request)

    if not clips:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tidak ada klip yang ditemukan dari video tersebut.",
        )

    from workers.worker import process_all_clips_task

    try:
        task = await process_all_clips_task.kiq(
            sources[0],
            _apply_plan_to_clips(clips, plan, request.target_language),
            request.target_language,
            get_request_id(),
            current_traceparent(),
            mix_sources=mix_sources,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengantre render video.",
        ) from exc

    return {
        "status": "processing",
        "task_id": task.task_id,
        "request_id": get_request_id(),
        "brief": brief,
        "queued_clips": len(clips),
        "mix_sources": mix_sources,
        "sources": sources,
    }
