"""Kompatibilitas lama: transkrip + hook lewat LangChain (provider bebas).

Nama modul dipertahankan agar import lama tidak rusak, tetapi tidak lagi
terikat pada Groq.
"""

import json

from backend.core.transcription import transcribe
from backend.services.model_discovery import get_text_model


def get_transcript_and_hooks(audio_path: str):
    transcript_text = transcribe(audio_path)
    if not transcript_text:
        return []

    prompt = f"""
Ini adalah transkrip video: {transcript_text}
Berikan 3 segmen paling seru berdurasi 30-60 detik.
Output HANYA array JSON dengan format:
[{{"start_time": detik_mulai, "end_time": detik_selesai, "title": "Judul Viral", "desc": "Deskripsi + hashtag"}}]
"""
    response = get_text_model(temperature=0.7).invoke(prompt)
    content = getattr(response, "content", str(response))
    try:
        return json.loads(content)
    except ValueError, TypeError:
        return []
