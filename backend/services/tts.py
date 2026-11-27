"""Text-to-Speech (TTS) — TEKS → SUARA (mesin bicara).

⚠️ JANGAN tertukar:
  - TTS = teks masuk, audio keluar  → modul ini (generate_tts)
  - STT = audio masuk, teks keluar  → backend.core.transcription (transcribe)
  - LLM = teks masuk, teks keluar   → backend.services.model_discovery (get_text_model)

Provider: Cartesia → Camb AI → gTTS (gratis).
Dipilih lewat ``TTS_PROVIDER`` (default ``auto`` = urutan di atas).

Dok:
- Cartesia https://docs.cartesia.ai/api-reference/tts/bytes
- Camb AI https://docs.camb.ai/api-reference/endpoint/create-tts-stream
"""

import os
import tempfile
from typing import Callable, Optional

import requests

from backend.core.env import load_env
from backend.log import logger

load_env("backend")

TTS_PROVIDERS = ("cartesia", "camb", "gtts")

CARTESIA_TTS_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = os.getenv("CARTESIA_VERSION", "2026-08-14")
CARTESIA_MODEL = os.getenv("CARTESIA_MODEL", "sonic-3.6")

CAMB_TTS_URL = "https://client.camb.ai/apis/tts-stream"
CAMB_VOICE_ID = int(os.getenv("CAMB_VOICE_ID", "147320"))
CAMB_MODEL = os.getenv("CAMB_MODEL", "mars-8.1-flash-beta")

TTS_LOCALE = {"id": "id-id", "en": "en-us"}


def tts_provider() -> str:
    """Provider TTS dari env; 'auto' berarti coba semua berurutan."""
    selected = os.getenv("TTS_PROVIDER", "auto").strip().lower()
    if selected not in {*TTS_PROVIDERS, "auto"}:
        raise ValueError(
            f"TTS_PROVIDER '{selected}' tidak dikenal. Pilih: auto, {', '.join(TTS_PROVIDERS)}"
        )
    return selected


def tts_cartesia(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    api_key = os.getenv("CARTESIA_API_KEY", "").strip()
    voice_id = os.getenv("CARTESIA_VOICE_ID", "").strip()
    if not api_key or not voice_id:
        return None
    payload = {
        "model_id": CARTESIA_MODEL,
        "transcript": text,
        "voice": {"id": voice_id},
        "language": TTS_LOCALE.get(lang, "en-us"),
        "output_format": {
            "container": "mp3",
            "sample_rate": 44100,
            "bit_rate": 128000,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Cartesia-Version": CARTESIA_VERSION,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            CARTESIA_TTS_URL, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()
        output_path = output_path or tempfile.mktemp(suffix=".mp3")
        with open(output_path, "wb") as file:
            file.write(response.content)
        return output_path
    except (requests.RequestException, OSError) as exc:
        logger.error(f"[TTS] Cartesia gagal: {exc}")
        return None


def tts_camb(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    api_key = os.getenv("CAMB_API_KEY", "").strip()
    if not api_key:
        return None
    payload = {
        "text": text,
        "language": TTS_LOCALE.get(lang, "en-us"),
        "voice_id": CAMB_VOICE_ID,
        "speech_model": CAMB_MODEL,
        "output_configuration": {"format": "mp3"},
    }
    try:
        response = requests.post(
            CAMB_TTS_URL,
            headers={"x-api-key": api_key},
            json=payload,
            timeout=60,
            stream=True,
        )
        response.raise_for_status()
        output_path = output_path or tempfile.mktemp(suffix=".mp3")
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        return output_path
    except (requests.RequestException, OSError) as exc:
        logger.error(f"[TTS] Camb AI gagal: {exc}")
        return None


def tts_gtts(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    try:
        from gtts import gTTS

        output_path = output_path or tempfile.mktemp(suffix=".mp3")
        gTTS(text=text, lang=lang, slow=False).save(output_path)
        return output_path
    except Exception as exc:
        logger.error(f"[TTS] gTTS gagal: {exc}")
        return None


def _tts_func(name: str) -> Callable[..., Optional[str]]:
    """Lookup runtime agar override/monkeypatch fungsi TTS bekerja."""
    return globals()[f"tts_{name}"]


def generate_tts(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    """Hasilkan audio dari teks memakai provider TTS terpilih."""
    selected = tts_provider()
    order = TTS_PROVIDERS if selected == "auto" else (selected,)
    for name in order:
        result = _tts_func(name)(text, lang, output_path)
        if result:
            from backend.core.audit import log_ai_call

            log_ai_call("tts", name)
            logger.info(f"[TTS] Berhasil via {name}.")
            return result
        from backend.core.audit import log_ai_call

        log_ai_call("tts", name, success=False)
        logger.warning(f"[TTS] {name} tidak tersedia, coba berikutnya.")
    return None
