import os

from fastapi import FastAPI, BackgroundTasks


# Import dari struktur baru
from utils.youtube import download_audio_only, check_and_get_youtube_subs
from core.ai_pipeline import process_video_ai_logic

from services.video_engine import crop_to_vertical_cpu

from pydantic import BaseModel

app = FastAPI(title="AI Clipper Backend API")


class VideoRequest(BaseModel):
    url: str
    user_query: str = "momen paling seru dan penting"  # Input default
    target_language: str = "id"


@app.post("/generate-clips")
async def generate_clips(request: VideoRequest, background_tasks: BackgroundTasks):

    transcript_text = None
    audio_path = None

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

    background_tasks.add_task(
        process_all_clips, request.url, clips_metadata, request.target_language
    )

    return {
        "status": "processing",
        "message": "AI selesai menganalisis. Memulai CPU rendering lokal.",
        "hooks_found": len(clips_metadata),
        "data": clips_metadata,
    }


def process_all_clips(video_url: str, clips_metadata: list, lang: str):
    # Untuk sementara kita print saja sebelum mesin FFmpeg benar-benar dihidupkan
    for index, clip in enumerate(clips_metadata):
        print(
            f"Persiapan render klip {index+1}: {clip.get('title_id')} ({clip.get('start_time')}s - {clip.get('end_time')}s)"
        )
        crop_to_vertical_cpu(
            input_video, output_video, clip["start_time"], clip["end_time"]
        )
