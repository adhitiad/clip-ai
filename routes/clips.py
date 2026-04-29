import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from utils.youtube import download_audio_only, check_and_get_youtube_subs
from core.ai_pipeline import process_video_ai_logic
from services.video_engine import process_clip
from utils.db import save_clip, save_clips_bulk, update_clip_score
from core.auth import get_db
from core.security import check_credits, consume_credits_atomic, refund_credits_atomic
from models.user import User
from sqlalchemy.orm import Session
from log import logger

router = APIRouter(prefix="/clips", tags=["Clip Management"])

class VideoRequest(BaseModel):
    url: str
    user_query: str = "momen paling seru dan penting"  # Input default
    target_language: str = "id"

class FeedbackRequest(BaseModel):
    clip_id: int
    score: int  # e.g., 1 for thumbs up, -1 for thumbs down

@router.post("/generate-clips")
async def generate_clips(
    request: VideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_credits)
):
    transcript_text = ""
    audio_path = ""

    # 1. Coba curi subtitle YouTube dulu (Kecepatan Instan)
    transcript_text = check_and_get_youtube_subs(request.url, request.target_language) or ""

    # 2. Jika gagal, unduh audio
    if not transcript_text:
        logger.info(f"Subtitle tidak tersedia untuk {request.url}, mengunduh audio...")
        audio_path = download_audio_only(request.url)

    # 3. Proses AI Pipeline (akan otomatis pakai Whisper jika transcript_text kosong)
    clips_metadata = process_video_ai_logic(
        audio_path=audio_path,
        user_query=request.user_query,
        transcript_text=transcript_text,
    )
    if not clips_metadata:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tidak ada klip yang ditemukan dari video tersebut.",
        )

    # Bersihkan file audio jika ada
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)

    from services.vector_store import upsert_clip_vector
    
    # ⚡ Bolt Optimization: Simpan konteks secara bulk (menghindari N+1 queries)
    clips_bulk_data = []
    for clip in clips_metadata:
        clips_bulk_data.append({
            "video_url": request.url,
            "topic": request.user_query,
            "start_time": clip.get("start_time", 0),
            "end_time": clip.get("end_time", 0),
            "title_en": clip.get("title_en", clip.get("title_id", "")),
            "desc_en": clip.get("desc_en", clip.get("desc_id", "")),
        })

    # Simpan sekaligus ke database
    db_ids = save_clips_bulk(clips_bulk_data, user_id=current_user.id)

    # Update metadata dan simpan ke Pinecone
    for i, clip in enumerate(clips_metadata):
        db_id = db_ids[i] if i < len(db_ids) else 0
        clip["clip_id"] = db_id
        
        # Simpan vektor kemiripan ke Pinecone
        if db_id > 0:
            upsert_clip_vector(
                clip_id=db_id, 
                topic=request.user_query, 
                title=clip.get("title_en", clip.get("title_id", "")), 
                desc=clip.get("desc_en", clip.get("desc_id", ""))
            )

    # 4. Antre tugas ke Celery
    from worker import process_all_clips_task
    if not consume_credits_atomic(db, current_user.id, amount=1):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Kredit Anda habis. Silakan upgrade plan atau isi ulang kredit Anda.",
        )
    try:
        task = process_all_clips_task.delay(request.url, clips_metadata, request.target_language)
    except Exception:
        refund_credits_atomic(db, current_user.id, amount=1)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengantre task render. Kredit Anda sudah dikembalikan.",
        )

    return {
        "status": "processing",
        "message": "AI selesai menganalisis. Memulai CPU rendering via Celery Task Queue.",
        "task_id": task.id,
        "hooks_found": len(clips_metadata),
        "data": clips_metadata,
    }

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Endpoint untuk memberi tahu AI jika hook tersebut sukses/viral.
    """
    update_clip_score(request.clip_id, request.score)
    return {"status": "success", "message": f"Feedback for clip {request.clip_id} recorded."}

def process_all_clips(video_url: str, clips_metadata: list, lang: str):
    # Menggunakan fungsi process_clip dari video_engine
    from utils.youtube import download_video_segment
    for index, clip in enumerate(clips_metadata):
        logger.info(f"Persiapan render klip {index+1}: {clip.get('title_id')} ({clip.get('start_time')}s - {clip.get('end_time')}s)")
        process_clip(video_url, clip, index+1, download_video_segment)
