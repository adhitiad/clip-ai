"""
routes/niche.py
================
Endpoint untuk:
  GET  /niche/trending          → Ambil topik trending dari Google RSS
  GET  /niche/suggest           → Analisis niche terbaik via AI
  GET  /niche/find-videos       → Cari video YouTube berdasarkan niche/query
  GET  /niche/search-web        → Cari berita/artikel web via Exa Search
  POST /niche/analyze-and-queue → Satu endpoint lengkap: trending → AI analysis → queue klip
"""

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.auth import get_current_active_user
from backend.core.request_id import get_request_id
from backend.core.telemetry import current_traceparent
from backend.core.validation import validate_search_type
from backend.log import logger
from backend.models.user import User

router = APIRouter(
    prefix="/niche",
    tags=["Niche & Discovery"],
    dependencies=[Depends(get_current_active_user)],
)


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────


class AutoQueueRequest(BaseModel):
    geo: str = "id"  # Negara Google Trends (id/us/global)
    niche_count: int = 3  # Berapa niche yang akan diproses
    videos_per_niche: int = 3  # Berapa video per niche
    user_query: str = "momen paling menarik dan viral"
    target_language: str = "id"
    min_duration_seconds: int = 120  # Filter video minimal 2 menit
    max_duration_seconds: int = 3600  # Filter video maksimal 1 jam


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────


@router.get("/trending")
async def get_trending(
    geo: str = Query(
        default="id", description="Kode negara: 'id', 'us', atau 'global'"
    ),
    max_items: int = Query(default=20, ge=5, le=50),
):
    """
    Ambil topik trending langsung dari Google Trends RSS.
    Tidak perlu API key, gratis, real-time.
    """
    from backend.utils.rss_google import get_trending_topics

    topics = await asyncio.to_thread(get_trending_topics, geo=geo, max_items=max_items)

    if not topics:
        raise HTTPException(
            status_code=503,
            detail="Gagal mengambil data Google Trends. Coba lagi beberapa saat.",
        )

    return {
        "status": "success",
        "geo": geo.upper(),
        "total": len(topics),
        "trending": topics,
    }


@router.get("/suggest")
async def suggest_niches(
    geo: str = Query(
        default="id", description="Kode negara: 'id', 'us', atau 'global'"
    ),
    max_trends: int = Query(default=20, ge=10, le=50),
    current_user: User = Depends(get_current_active_user),
):
    """
    Ambil trending → analisis AI → kembalikan 5 niche terbaik beserta
    saran hook konten dan query pencarian video.
    """
    from backend.utils.rss_google import analyze_niches_with_ai, get_trending_topics

    topics = await asyncio.to_thread(get_trending_topics, geo=geo, max_items=max_trends)
    if not topics:
        raise HTTPException(status_code=503, detail="Gagal ambil Google Trends.")

    niches = await asyncio.to_thread(analyze_niches_with_ai, topics)

    return {
        "status": "success",
        "geo": geo.upper(),
        "trending_analyzed": len(topics),
        "niches_recommended": niches,
    }


@router.get("/find-videos")
async def find_videos(
    query: str = Query(..., description="Kata kunci pencarian video YouTube"),
    max_results: int = Query(default=10, ge=1, le=30),
    min_duration: int = Query(default=60, description="Durasi minimal video (detik)"),
    max_duration: int = Query(
        default=7200, description="Durasi maksimal video (detik)"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """
    Cari video YouTube berdasarkan query menggunakan yt-dlp (tanpa API key).
    Mengembalikan list video lengkap dengan URL, thumbnail, durasi, dll.
    """
    from backend.utils.rss_google import search_youtube_videos_rss

    videos = await asyncio.to_thread(
        search_youtube_videos_rss, query=query, max_results=max_results * 2
    )

    # Filter berdasarkan durasi jika tersedia
    filtered = []
    for v in videos:
        dur = v.get("duration")
        if dur is not None:
            if min_duration <= dur <= max_duration:
                filtered.append(v)
        else:
            filtered.append(v)  # Jika durasi tidak diketahui, tetap masukkan

    return {
        "status": "success",
        "query": query,
        "total_found": len(filtered[:max_results]),
        "videos": filtered[:max_results],
    }


@router.get("/search-web")
async def search_web(
    query: str = Query(..., description="Kata kunci berita/artikel web"),
    num_results: int = Query(default=10, ge=1, le=20),
    search_type: str = Query(
        default="auto",
        description="auto | fast | deep-lite | deep | deep-reasoning | instant",
    ),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Cari berita/artikel web terbaru menggunakan Exa.
    """
    from backend.utils.exa_search import search_news_with_exa

    try:
        search_type = validate_search_type(search_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        results = await asyncio.to_thread(
            search_news_with_exa,
            query=query,
            num_results=num_results,
            search_type=search_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"[Exa] Gagal search web untuk query '{query}': {e}")
        raise HTTPException(
            status_code=502, detail="Gagal mengambil hasil dari Exa Search."
        ) from e

    return {
        "status": "success",
        "query": query,
        "search_type": search_type,
        "total_found": len(results),
        "results": results,
    }


def _collect_jobs_sync(
    request: AutoQueueRequest, user_id: int
) -> tuple[list[dict], list[dict], list[dict]]:
    from backend.core.ai_pipeline import process_video_ai_logic
    from backend.utils.db import save_clip
    from backend.utils.rss_google import (
        analyze_niches_with_ai,
        get_trending_topics,
        search_youtube_videos_rss,
    )
    from backend.utils.youtube import check_and_get_youtube_subs, download_audio_only

    # STEP 1: Google Trends
    logger.info(
        f"[Auto-Queue] Step 1: Ambil trending Google ({request.geo.upper()})..."
    )
    topics = get_trending_topics(geo=request.geo, max_items=20)
    if not topics:
        raise HTTPException(status_code=503, detail="Gagal ambil Google Trends.")

    # STEP 2: AI Niche Analysis
    logger.info(f"[Auto-Queue] Step 2: AI menganalisis {len(topics)} topik...")
    niches = analyze_niches_with_ai(topics)
    if not niches:
        raise HTTPException(status_code=500, detail="AI gagal menganalisis niche.")

    selected_niches = niches[: request.niche_count]
    jobs: list[dict] = []

    # STEP 3 & 4: Per Niche → Cari Video → Siapkan klip
    for niche_data in selected_niches:
        search_query = niche_data.get("search_query", niche_data.get("niche", ""))
        niche_name = niche_data.get("niche", "Unknown")

        logger.info(
            f"[Auto-Queue] Step 3: Cari video untuk niche '{niche_name}' (query: '{search_query}')..."
        )
        videos = search_youtube_videos_rss(
            query=search_query,
            max_results=request.videos_per_niche * 3,  # Ambil lebih untuk difilter
        )

        filtered_videos = []
        for video in videos:
            dur = video.get("duration")
            if dur is not None:
                if request.min_duration_seconds <= dur <= request.max_duration_seconds:
                    filtered_videos.append(video)
            else:
                filtered_videos.append(video)

        for video in filtered_videos[: request.videos_per_niche]:
            video_url = video["url"]
            logger.info(
                f"[Auto-Queue] Step 4: AI Pipeline untuk video: {video['title'][:60]}..."
            )
            try:
                transcript_text = (
                    check_and_get_youtube_subs(video_url, request.target_language) or ""
                )
                audio_path = ""
                if not transcript_text:
                    audio_path = download_audio_only(video_url)

                clips_metadata = process_video_ai_logic(
                    audio_path=audio_path,
                    user_query=request.user_query,
                    transcript_text=transcript_text,
                )
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)

                if not clips_metadata:
                    logger.info("  ⚠️ Tidak ada klip ditemukan dari video ini.")
                    continue

                for clip in clips_metadata:
                    db_id = save_clip(
                        video_url=video_url,
                        topic=f"[{niche_name}] {request.user_query}",
                        start_time=clip.get("start_time", 0),
                        end_time=clip.get("end_time", 0),
                        title_en=clip.get("title_en", clip.get("title_id", "")),
                        desc_en=clip.get("desc_en", clip.get("desc_id", "")),
                        user_id=user_id,
                    )
                    clip["clip_id"] = db_id

                jobs.append(
                    {
                        "niche": niche_name,
                        "video_title": video["title"],
                        "video_url": video_url,
                        "clips_metadata": clips_metadata,
                    }
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.error(f"  ❌ Error saat memproses video {video_url}: {exc}")
                continue

    return jobs, niches, selected_niches


@router.post("/analyze-and-queue")
async def analyze_and_queue(
    request: AutoQueueRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    🤖 Pipeline Otomatis Penuh:
      1. Ambil trending Google (geo yang dipilih)
      2. AI analisis → rekomendasikan N niche terbaik
      3. Cari video YouTube untuk setiap niche
      4. Queue rendering klip via Taskiq untuk setiap video yang ditemukan

    Seluruh kerja sinkron berjalan di thread; hanya ``kiq()`` yang di-await.
    """
    jobs, niches, selected_niches = await asyncio.to_thread(
        _collect_jobs_sync, request, current_user.id
    )

    from workers.worker import process_all_clips_task

    queued_tasks = []
    for job in jobs:
        try:
            task = await process_all_clips_task.kiq(
                job["video_url"],
                job["clips_metadata"],
                request.target_language,
                get_request_id(),
                current_traceparent(),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mengantre task render.",
            ) from exc

        queued_tasks.append(
            {
                "niche": job["niche"],
                "video_title": job["video_title"],
                "video_url": job["video_url"],
                "clips_found": len(job["clips_metadata"]),
                "task_id": task.task_id,
            }
        )

    return {
        "status": "success" if queued_tasks else "partial",
        "geo": request.geo.upper(),
        "niches_analyzed": len(niches),
        "niches_processed": len(selected_niches),
        "total_tasks_queued": len(queued_tasks),
        "tasks": queued_tasks,
        "message": (
            f"✅ {len(queued_tasks)} video sedang diproses di background."
            if queued_tasks
            else "⚠️ Tidak ada video yang berhasil di-queue."
        ),
    }
