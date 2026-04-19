"""
routes/niche.py
================
Endpoint untuk:
  GET  /niche/trending          → Ambil topik trending dari Google RSS
  GET  /niche/suggest           → Analisis niche terbaik via AI
  GET  /niche/find-videos       → Cari video YouTube berdasarkan niche/query
  POST /niche/analyze-and-queue → Satu endpoint lengkap: trending → AI analysis → queue klip
"""

import os
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.security import require_plan, check_credits, deduct_credit
from core.auth import get_db
from models.user import UserPlan, User
from sqlalchemy.orm import Session
from log import logger

router = APIRouter(prefix="/niche", tags=["Niche & Discovery"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class AutoQueueRequest(BaseModel):
    geo: str = "id"                      # Negara Google Trends (id/us/global)
    niche_count: int = 3                 # Berapa niche yang akan diproses
    videos_per_niche: int = 3            # Berapa video per niche
    user_query: str = "momen paling menarik dan viral"
    target_language: str = "id"
    min_duration_seconds: int = 120      # Filter video minimal 2 menit
    max_duration_seconds: int = 3600     # Filter video maksimal 1 jam


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.get("/trending")
async def get_trending(
    geo: str = Query(default="id", description="Kode negara: 'id', 'us', atau 'global'"),
    max_items: int = Query(default=20, ge=5, le=50),
):
    """
    Ambil topik trending langsung dari Google Trends RSS.
    Tidak perlu API key, gratis, real-time.
    """
    from utils.rss_google import get_trending_topics
    topics = get_trending_topics(geo=geo, max_items=max_items)

    if not topics:
        raise HTTPException(
            status_code=503,
            detail="Gagal mengambil data Google Trends. Coba lagi beberapa saat."
        )

    return {
        "status": "success",
        "geo": geo.upper(),
        "total": len(topics),
        "trending": topics,
    }


@router.get("/suggest")
async def suggest_niches(
    geo: str = Query(default="id", description="Kode negara: 'id', 'us', atau 'global'"),
    max_trends: int = Query(default=20, ge=10, le=50),
    current_user: User = Depends(require_plan(UserPlan.PREMIUM))
):
    """
    Ambil trending → analisis AI → kembalikan 5 niche terbaik beserta
    saran hook konten dan query pencarian video.
    """
    from utils.rss_google import get_trending_topics, analyze_niches_with_ai

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY belum dikonfigurasi.")

    topics = get_trending_topics(geo=geo, max_items=max_trends)
    if not topics:
        raise HTTPException(status_code=503, detail="Gagal ambil Google Trends.")

    niches = analyze_niches_with_ai(topics, GROQ_API_KEY)

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
    max_duration: int = Query(default=7200, description="Durasi maksimal video (detik)"),
    current_user: User = Depends(require_plan(UserPlan.PREMIUM))
):
    """
    Cari video YouTube berdasarkan query menggunakan yt-dlp (tanpa API key).
    Mengembalikan list video lengkap dengan URL, thumbnail, durasi, dll.
    """
    from utils.rss_google import search_youtube_videos_rss

    videos = search_youtube_videos_rss(query=query, max_results=max_results * 2)

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


@router.post("/analyze-and-queue")
async def analyze_and_queue(
    request: AutoQueueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_credits)
):
    # Cek level plan tambahan (Require BUSINESS)
    from core.security import require_plan
    await require_plan(UserPlan.BUSINESS)(current_user)
    """
    🤖 Pipeline Otomatis Penuh:
      1. Ambil trending Google (geo yang dipilih)
      2. AI analisis → rekomendasikan N niche terbaik
      3. Cari video YouTube untuk setiap niche
      4. Queue rendering klip via Celery untuk setiap video yang ditemukan
      
    Ini adalah endpoint "satu tekan" untuk produksi konten tanpa intervensi manual.
    """
    from utils.rss_google import (
        get_trending_topics,
        analyze_niches_with_ai,
        search_youtube_videos_rss,
    )
    from core.ai_pipeline import process_video_ai_logic
    from utils.youtube import check_and_get_youtube_subs, download_audio_only
    from utils.db import save_clip
    from worker import process_all_clips_task

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY belum dikonfigurasi.")

    # STEP 1: Google Trends
    logger.info(f"[Auto-Queue] Step 1: Ambil trending Google ({request.geo.upper()})...")
    topics = get_trending_topics(geo=request.geo, max_items=20)
    if not topics:
        raise HTTPException(status_code=503, detail="Gagal ambil Google Trends.")

    # STEP 2: AI Niche Analysis
    logger.info(f"[Auto-Queue] Step 2: AI menganalisis {len(topics)} topik...")
    niches = analyze_niches_with_ai(topics, GROQ_API_KEY)
    if not niches:
        raise HTTPException(status_code=500, detail="AI gagal menganalisis niche.")

    selected_niches = niches[: request.niche_count]

    # STEP 3 & 4: Per Niche → Cari Video → Queue
    queued_tasks = []

    for niche_data in selected_niches:
        search_query = niche_data.get("search_query", niche_data.get("niche", ""))
        niche_name   = niche_data.get("niche", "Unknown")

        logger.info(f"[Auto-Queue] Step 3: Cari video untuk niche '{niche_name}' (query: '{search_query}')...")
        videos = search_youtube_videos_rss(
            query=search_query,
            max_results=request.videos_per_niche * 3,  # Ambil lebih untuk difilter
        )

        # Filter durasi
        filtered_videos = []
        for v in videos:
            dur = v.get("duration")
            if dur is not None:
                if request.min_duration_seconds <= dur <= request.max_duration_seconds:
                    filtered_videos.append(v)
            else:
                filtered_videos.append(v)

        videos_to_process = filtered_videos[: request.videos_per_niche]

        if not videos_to_process:
            logger.info(f"[Auto-Queue] ⚠️ Tidak ada video yang cocok untuk niche '{niche_name}'.")
            continue

        for video in videos_to_process:
            video_url = video["url"]
            logger.info(f"[Auto-Queue] Step 4: AI Pipeline untuk video: {video['title'][:60]}...")

            try:
                # Coba ambil subtitle dulu (cepat)
                transcript_text = check_and_get_youtube_subs(video_url, request.target_language) or ""
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
                    logger.info(f"  ⚠️ Tidak ada klip ditemukan dari video ini.")
                    continue

                # Simpan ke DB
                for clip in clips_metadata:
                    db_id = save_clip(
                        video_url=video_url,
                        topic=f"[{niche_name}] {request.user_query}",
                        start_time=clip.get("start_time", 0),
                        end_time=clip.get("end_time", 0),
                        title_en=clip.get("title_en", clip.get("title_id", "")),
                        desc_en=clip.get("desc_en", clip.get("desc_id", "")),
                    )
                    clip["clip_id"] = db_id

                # Queue ke Celery
                task = process_all_clips_task.delay(
                    video_url, clips_metadata, request.target_language
                )

                # PEMOTONGAN KREDIT: 1 kredit per video yang berhasil di-queue
                deduct_credit(db, current_user)

                queued_tasks.append({
                    "niche": niche_name,
                    "video_title": video["title"],
                    "video_url": video_url,
                    "clips_found": len(clips_metadata),
                    "task_id": task.id,
                })

            except Exception as e:
                logger.error(f"  ❌ Error saat memproses video {video_url}: {e}")
                continue

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
