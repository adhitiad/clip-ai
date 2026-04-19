"""
70b
"""

import os
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from routes.clips import app as clips_app


app = FastAPI(title="AI Clipper Backend API")


def process_all_clips(video_url: str, clips_metadata: list, lang: str):
    # Untuk sementara kita print saja sebelum mesin FFmpeg benar-benar dihidupkan
    for index, clip in enumerate(clips_metadata):
        print(
            f"Persiapan render klip {index+1}: {clip.get('title_id')} ({clip.get('start_time')}s - {clip.get('end_time')}s)"
        )
        # crop_to_vertical_cpu(input_video, output_video, clip['start_time'], clip['end_time'])


if __name__ == "__main__":
    # Pastikan folder temp/ eksis sebelum server menyala
    os.makedirs("temp", exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)
