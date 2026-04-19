from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from utils.youtube import download_audio_only
from utils.groq_ai import get_transcript_and_hooks
from services.video_engine import process_clip

app = FastAPI(title="AI Clipper Backend API")


class VideoRequest(BaseModel):
    url: str
    target_language: str = "id"


@app.post("/api/v1/generate-clips")
async def generate_clips(request: VideoRequest, background_tasks: BackgroundTasks):
    # 1. Download Audio saja agar cepat
    audio_path = download_audio_only(request.url)

    # 2. Kirim audio ke Groq (Whisper) & Llama 3 untuk dapat 10 Hooks
    # Mengembalikan list dictionary: [{"start": 10, "end": 40, "title": "...", "desc": "..."}]
    clips_metadata = get_transcript_and_hooks(audio_path)

    # Karena rendering di CPU sangat lambat, kita jalankan di background
    # Frontend akan menerima response langsung, sementara CPU merender
    background_tasks.add_task(
        process_all_clips, request.url, clips_metadata, request.target_language
    )

    return {
        "status": "processing",
        "message": "AI sedang merender klip. Membutuhkan waktu beberapa menit (CPU mode).",
        "hooks_found": len(clips_metadata),
        "data": clips_metadata,
    }


def process_all_clips(video_url: str, clips_metadata: list, lang: str):
    # Proses iterasi pemotongan video menggunakan CPU (FFmpeg & MediaPipe)
    for index, clip in enumerate(clips_metadata):
        # Di sinilah fungsi video_engine.py dipanggil
        print(f"Memproses klip {index+1}...")
        pass


if __name__ == "__main__":
    uvicorn.run(app, host="[IP_ADDRESS]", port=8000)
