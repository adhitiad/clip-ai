"""Smoke render FFmpeg sungguhan dengan transkrip asli.

Jalankan dari root repo:
    uv run python scripts/smoke_render.py

Transkripsi memakai backend/core/transcription.py:
  - ada OPENAI_API_KEY  -> OpenAI Whisper (verbose_json, word timestamps)
  - ada GROQ_API_KEY    -> Groq Whisper (segmen -> kata)
  - keduanya kosong     -> subtitle kosong (render tetap sukses)
Isi salah satu key di .env agar caption mengikuti kata yang benar-benar terucap.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ.setdefault("SECRET_KEY", "smoke-render-only-secret")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./.smoke.db")

    from backend.core.env import load_env

    load_env("backend")

    from backend.core.transcription import transcribe_words
    from backend.services.video_engine import process_clip

    has_key = bool(
        os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
    )
    if not has_key:
        print(
            "PERINGATAN: OPENAI_API_KEY/GROQ_API_KEY kosong -> subtitle akan kosong. "
            "Isi salah satu di .env untuk transkrip asli."
        )

    source = ROOT / "temp" / "sample_input.mp4"
    if not source.is_file():
        print("temp/sample_input.mp4 belum ada. Buat dulu dengan FFmpeg.")
        return 1

    def local_download(_url: str, _start: float, _end: float, output_path: str) -> bool:
        shutil.copyfile(source, output_path)
        return True

    # Transkrip asli dari audio.
    def real_transcription(audio_path: str) -> list:
        return transcribe_words(audio_path)

    import backend.utils.captioning as captioning

    captioning.get_word_level_transcription = real_transcription

    metadata = {
        "title_id": "Smoke Render Lokal",
        "title_en": "Smoke Render Lokal",
        "desc_id": "Render nyata via FFmpeg + transkrip asli",
        "start_time": 0,
        "end_time": 6,
    }

    print("== mulai render sungguhan ==")
    result = process_clip("local://sample", metadata, 1, local_download)
    print("== selesai ==")
    print("output:", result)
    if result and (ROOT / result).is_file():
        print(f"file ada: {(ROOT / result).stat().st_size} bytes")
        return 0
    print("Render gagal: file output tidak ditemukan.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
