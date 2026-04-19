import os

from fastapi import FastAPI, BackgroundTasks, APIRouter
from pydantic import BaseModel

from utils.youtube import download_audio_only, check_and_get_youtube_subs
from core.ai_pipeline import process_video_ai_logic
from services.video_engine import process_clip, crop_to_vertical_cpu
from utils.db import save_clip, update_clip_score

router = APIRouter()

class VideoRequest(BaseModel):
    url: str
    user_query: str = "momen paling seru dan penting"  # Input default
    target_language: str = "id"

class FeedbackRequest(BaseModel):
    clip_id: int
    score: int  # e.g., 1 for thumbs up, -1 for thumbs down

@router.post("/generate-clips")
async def generate_clips(request: VideoRequest, background_tasks: BackgroundTasks):
    transcript_text = ""
    audio_path = ""

    # 1. Coba curi subtitle YouTube dulu (Kecepatan Instan)
    transcript_text = check_and_get_youtube_subs(request.url, request.target_language)

    # 2. Jika gagal, unduh audio
    if not transcript_text:
        print("Subtitle tidak tersedia, mengunduh audio...")
        audio_path = download_audio_only(request.url)

    # 3. Proses AI Pipeline (akan otomatis pakai Whisper jika transcript_text kosong)
    clips_metadata = process_video_ai_logic(
        audio_path=audio_path,
        user_query=request.user_query,
        transcript_text=transcript_text,
    )

    # Bersihkan file audio jika ada
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)

    from services.vector_store import upsert_clip_vector
    
    # Simpan konteks (Continuous Learning) untuk setiap klip ke Database
    for clip in clips_metadata:
        db_id = save_clip(
            video_url=request.url,
            topic=request.user_query,
            start_time=clip.get("start_time", 0),
            end_time=clip.get("end_time", 0),
            title_en=clip.get("title_en", clip.get("title_id", "")),  # Fallback
            desc_en=clip.get("desc_en", clip.get("desc_id", ""))
        )
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
    task = process_all_clips_task.delay(request.url, clips_metadata, request.target_language)

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
        print(f"Persiapan render klip {index+1}: {clip.get('title_id')} ({clip.get('start_time')}s - {clip.get('end_time')}s)")
        process_clip(video_url, clip, index+1, download_video_segment)
