"""Speech-to-Text (STT) — SUARA → TEKS (mesin mendengar lalu menulis).

⚠️ JANGAN tertukar:
  - STT = audio masuk, teks keluar  → modul ini (transcribe / transcribe_words)
  - TTS = teks masuk, audio keluar  → backend.services.tts (generate_tts)
  - LLM = teks masuk, teks keluar   → backend.services.model_discovery (get_text_model)

Provider: Camb AI (batch, timestamp) → OpenAI Whisper → Groq Whisper.
Dipilih lewat ``STT_PROVIDER`` (default ``auto`` = urutan di atas).

Dok Camb: https://docs.camb.ai/api-reference/endpoint/create-transcription.md
"""

import os
import time

import requests

from backend.core.env import load_env
from backend.log import logger

load_env("backend")

STT_PROVIDERS = ("camb", "openai", "groq")


def stt_provider() -> str:
    """Provider STT dari env; 'auto' berarti coba semua berurutan."""
    selected = os.getenv("STT_PROVIDER", "auto").strip().lower()
    if selected not in {*STT_PROVIDERS, "auto"}:
        raise ValueError(
            f"STT_PROVIDER '{selected}' tidak dikenal. Pilih: auto, {', '.join(STT_PROVIDERS)}"
        )
    return selected


OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
CAMB_BASE = "https://client.camb.ai/apis"


def _camb_headers(api_key: str) -> dict:
    return {"x-api-key": api_key}


def _camb_transcribe(audio_path: str, api_key: str, language: str = "") -> list[dict]:
    """Kirim audio ke Camb, polling hingga SUCCESS, kembalikan segmen."""
    lang = language or os.getenv("CAMB_STT_LANGUAGE", "auto").strip() or "auto"
    data = {
        "language": lang,
        "transcription_mode": os.getenv("CAMB_STT_MODE", "fast"),
        "run_audio_cleaning": "false",
        "formatting_options": (
            '{"max_segment_duration_in_seconds":6,'
            '"min_segment_duration_in_seconds":1,'
            '"max_characters_in_segment":42}'
        ),
    }
    with open(audio_path, "rb") as file:
        response = requests.post(
            f"{CAMB_BASE}/transcribe",
            headers=_camb_headers(api_key),
            data=data,
            files={"media_file": (os.path.basename(audio_path), file)},
            timeout=60,
        )
    response.raise_for_status()
    task_id = response.json().get("task_id")
    if not task_id:
        raise RuntimeError("Camb tidak mengembalikan task_id")

    deadline = time.monotonic() + 180
    run_id = None
    while time.monotonic() < deadline:
        status = requests.get(
            f"{CAMB_BASE}/transcribe/{task_id}",
            headers=_camb_headers(api_key),
            timeout=30,
        )
        status.raise_for_status()
        payload = status.json()
        state = payload.get("status")
        if state == "SUCCESS":
            run_id = payload.get("run_id")
            break
        if state in {"ERROR", "TIMEOUT", "PAYMENT_REQUIRED"}:
            raise RuntimeError(f"Camb transkrip gagal: {state} {payload}")
        time.sleep(3)
    if not run_id:
        raise TimeoutError("Camb transkrip timeout")

    result = requests.get(
        f"{CAMB_BASE}/transcription-result/{run_id}",
        headers=_camb_headers(api_key),
        timeout=30,
    )
    result.raise_for_status()
    items = result.json().get("transcript", [])
    return [
        {
            "start": float(item.get("start", 0)),
            "end": float(item.get("end", 0)),
            "text": str(item.get("text", "")).strip(),
        }
        for item in items
        if str(item.get("text", "")).strip()
    ]


def _post_transcription(url: str, api_key: str, audio_path: str) -> dict | None:
    with open(audio_path, "rb") as file:
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (os.path.basename(audio_path), file, "audio/mpeg")},
                data={
                    "model": "whisper-1" if "openai.com" in url else "whisper-large-v3",
                    "response_format": "verbose_json",
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning(f"[Transkrip] Gagal ({url}): {exc}")
            return None


def _segments_from_openai_groq(data: dict) -> list[dict]:
    result = []
    for segment in data.get("segments", []):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        result.append(
            {
                "start": float(segment.get("start", 0)),
                "end": float(segment.get("end", 0)),
                "text": text,
            }
        )
    return result


def get_segments(audio_path: str) -> list[dict]:
    """Segmen {start,end,text} dari provider pertama yang aktif."""
    selected = stt_provider()
    order = STT_PROVIDERS if selected == "auto" else (selected,)
    endpoints = {
        "openai": (
            "OpenAI",
            os.getenv("OPENAI_API_KEY", "").strip(),
            OPENAI_TRANSCRIBE_URL,
        ),
        "groq": ("Groq", os.getenv("GROQ_API_KEY", "").strip(), GROQ_TRANSCRIBE_URL),
    }

    if "camb" in order:
        camb_key = os.getenv("CAMB_API_KEY", "").strip()
        if camb_key:
            try:
                segments = _camb_transcribe(audio_path, camb_key)
                if segments:
                    from backend.core.audit import log_ai_call

                    log_ai_call("stt", "camb")
                    logger.info(f"[STT] Segmen berhasil via Camb AI ({len(segments)}).")
                    return segments
            except (
                requests.RequestException,
                RuntimeError,
                TimeoutError,
                ValueError,
            ) as exc:
                logger.warning(f"[STT] Camb gagal: {exc}")

    for name in order:
        if name not in endpoints:
            continue
        provider, key, url = endpoints[name]
        if not key:
            continue
        data = _post_transcription(url, key, audio_path)
        if not data:
            continue
        segments = _segments_from_openai_groq(data)
        if segments:
            from backend.core.audit import log_ai_call

            log_ai_call("stt", name)
            logger.info(f"[Transkrip] Segmen berhasil via {provider}.")
            return segments
        if data.get("text"):
            return [{"start": 0.0, "end": 0.0, "text": data["text"]}]

    logger.warning("[Transkrip] Tidak ada provider aktif; kembalikan segmen kosong.")
    return []


def transcribe(audio_path: str) -> str:
    """Teks transkrip penuh."""
    return " ".join(segment["text"] for segment in get_segments(audio_path))


def transcribe_segments(audio_path: str) -> list[dict]:
    """Segmen dengan timestamp (dipakai dubbing)."""
    return get_segments(audio_path)


def transcribe_words(audio_path: str) -> list[dict]:
    """Kata-per-kata untuk subtitle dinamis (dipecah dari segmen)."""
    words = []
    for segment in get_segments(audio_path):
        text = segment["text"].strip()
        if not text:
            continue
        parts = text.split()
        duration = max(0.1, segment["end"] - segment["start"])
        step = duration / max(len(parts), 1)
        for index, word in enumerate(parts):
            words.append(
                {
                    "text": word,
                    "start": segment["start"] + index * step,
                    "end": segment["start"] + (index + 1) * step,
                }
            )
    return words
