import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.core.ai_pipeline import process_video_ai_logic
from backend.core.auth import get_current_active_user, get_db
from backend.core.rate_limit import check_rate_limit
from backend.core.request_id import get_request_id
from backend.core.telemetry import current_traceparent
from backend.log import logger
from backend.models.clip import Clip
from backend.models.user import User
from backend.services.video_engine import process_clip
from backend.utils.db import save_clip, update_clip_score
from backend.utils.youtube import check_and_get_youtube_subs, download_audio_only

router = APIRouter(prefix="/clips", tags=["Clip Management"])


class VideoRequest(BaseModel):
    url: str
    user_query: str = "momen paling seru dan penting"  # Input default
    target_language: str = "id"


class FeedbackRequest(BaseModel):
    clip_id: int
    score: int  # e.g., 1 for thumbs up, -1 for thumbs down


def _prepare_clips_sync(
    video_url: str, user_query: str, target_language: str, user_id: int
) -> list[dict]:
    from backend.services.vector_store import upsert_clip_vector

    transcript_text = check_and_get_youtube_subs(video_url, target_language) or ""
    audio_path = ""
    if not transcript_text:
        logger.info(f"Subtitle tidak tersedia untuk {video_url}, mengunduh audio...")
        audio_path = download_audio_only(video_url)

    clips_metadata = process_video_ai_logic(
        audio_path=audio_path,
        user_query=user_query,
        transcript_text=transcript_text,
    )
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)

    for clip in clips_metadata:
        db_id = save_clip(
            video_url=video_url,
            topic=user_query,
            start_time=clip.get("start_time", 0),
            end_time=clip.get("end_time", 0),
            title_en=clip.get("title_en", clip.get("title_id", "")),
            desc_en=clip.get("desc_en", clip.get("desc_id", "")),
            user_id=user_id,
        )
        clip["clip_id"] = db_id
        if db_id > 0:
            upsert_clip_vector(
                clip_id=db_id,
                topic=user_query,
                title=clip.get("title_en", clip.get("title_id", "")),
                desc=clip.get("desc_en", clip.get("desc_id", "")),
            )
    return clips_metadata


@router.post("/generate-clips")
async def generate_clips(
    request: VideoRequest,
    current_user: User = Depends(get_current_active_user),
):
    try:
        check_rate_limit("clips")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None
    clips_metadata = await asyncio.to_thread(
        _prepare_clips_sync,
        request.url,
        request.user_query,
        request.target_language,
        current_user.id,
    )
    if not clips_metadata:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tidak ada klip yang ditemukan dari video tersebut.",
        )

    # 4. Antre tugas ke Taskiq
    from workers.worker import process_all_clips_task

    try:
        task = await process_all_clips_task.kiq(
            request.url,
            clips_metadata,
            request.target_language,
            get_request_id(),
            current_traceparent(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengantre task render.",
        ) from exc

    return {
        "status": "processing",
        "message": "AI selesai menganalisis. Memulai render via Taskiq Task Queue.",
        "task_id": task.task_id,
        "request_id": get_request_id(),
        "hooks_found": len(clips_metadata),
        "data": clips_metadata,
    }


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    _current_user: User = Depends(get_current_active_user),
):
    """
    Endpoint untuk memberi tahu AI jika hook tersebut sukses/viral.
    """
    await asyncio.to_thread(update_clip_score, request.clip_id, request.score)
    return {
        "status": "success",
        "message": f"Feedback for clip {request.clip_id} recorded.",
    }


def process_all_clips(video_url: str, clips_metadata: list, lang: str):
    # Menggunakan fungsi process_clip dari video_engine
    from backend.utils.youtube import download_video_segment

    for index, clip in enumerate(clips_metadata):
        logger.info(
            f"Persiapan render klip {index + 1}: {clip.get('title_id')} ({clip.get('start_time')}s - {clip.get('end_time')}s)"
        )
        process_clip(video_url, clip, index + 1, download_video_segment)


class ClipOut(BaseModel):
    id: int
    video_url: str | None = None
    topic: str | None = None
    start_time: int
    end_time: int
    title_en: str | None = None
    desc_en: str | None = None
    score: int
    user_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ClipUpdate(BaseModel):
    title_en: str | None = None
    desc_en: str | None = None
    score: int | None = None


@router.get("", response_model=list[ClipOut])
def list_clips(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    return db.query(Clip).order_by(Clip.id.desc()).offset(offset).limit(limit).all()


def _get_clip(db: Session, clip_id: int) -> Clip:
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip tidak ditemukan.")
    return clip


@router.get("/{clip_id}", response_model=ClipOut)
def get_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    return _get_clip(db, clip_id)


@router.patch("/{clip_id}", response_model=ClipOut)
def update_clip(
    clip_id: int,
    request: ClipUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    clip = _get_clip(db, clip_id)
    for field, value in request.model_dump(exclude_none=True).items():
        setattr(clip, field, value)
    db.commit()
    db.refresh(clip)
    return clip


@router.delete("/{clip_id}")
def delete_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    clip = _get_clip(db, clip_id)
    db.delete(clip)
    db.commit()
    return {"status": "success", "clip_id": clip_id}
