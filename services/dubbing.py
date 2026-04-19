"""
services/dubbing.py
====================
AI Voice-Over Auto Dubbing Engine

Pipeline:
  1. Groq Whisper → transkripsi + segmen waktu
  2. Groq LLaMA → terjemahkan teks ke target bahasa
  3. ElevenLabs API → TTS suara realistis (primary)
     Coqui TTS (gTTS fallback) → jika ElevenLabs tidak dikonfigurasi
  4. FFmpeg → replace audio track asli dengan audio dubbing,
              pitch/speed adjust otomatis sesuai durasi klip

Variabel ENV yang dibutuhkan:
  - ELEVENLABS_API_KEY (opsional, jika kosong → fallback ke gTTS)
  - GROQ_API_KEY (wajib)
"""

import os
import json
import time
import tempfile
import subprocess
import requests
from pathlib import Path
from typing import Optional

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# ElevenLabs default voice IDs (bisa diganti)
ELEVENLABS_VOICES = {
    "id": "pNInz6obpgDQGcFmaJgB",  # Adam – natural, cocok untuk Indo narasi
    "en": "EXAVITQu4vr4xnSDxMaL",  # Bella – clear English
    "default": "pNInz6obpgDQGcFmaJgB",
}
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Transkripsi dengan timestamp per segmen
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_with_segments(audio_path: str) -> list[dict]:
    """
    Transkripsi audio menggunakan Groq Whisper, kembalikan per segmen:
    [{"start": float, "end": float, "text": str}]
    """
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    print("[Dubbing] Step 1: Transkripsi dengan Groq Whisper...")
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(audio_path, f.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )
    segments = getattr(result, "segments", []) or []
    return [
        {"start": s.get("start", 0), "end": s.get("end", 0), "text": s.get("text", "").strip()}
        for s in segments if s.get("text", "").strip()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Translate teks ke bahasa target
# ─────────────────────────────────────────────────────────────────────────────

def translate_segments(segments: list[dict], target_lang: str = "id") -> list[dict]:
    """
    Terjemahkan teks setiap segmen ke bahasa target menggunakan LLaMA via Groq.
    target_lang: 'id' (Indonesia) atau 'en' (English)
    """
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    lang_name = "Indonesian" if target_lang == "id" else "English"
    full_text = "\n".join([f"[{i}] {s['text']}" for i, s in enumerate(segments)])

    print(f"[Dubbing] Step 2: Menerjemahkan {len(segments)} segmen ke {lang_name}...")

    prompt = f"""Translate the following numbered segments to {lang_name}.
Keep the numbering format exactly [0], [1], etc.
Keep the translations natural and conversational, suitable for video narration.
Respond ONLY with the translated segments, nothing else.

{full_text}"""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192",
        temperature=0.3,
    )

    translated_text = response.choices[0].message.content.strip()
    translated_lines = {}
    for line in translated_text.split("\n"):
        line = line.strip()
        if line.startswith("[") and "]" in line:
            try:
                idx_end = line.index("]")
                idx = int(line[1:idx_end])
                text = line[idx_end + 1:].strip()
                translated_lines[idx] = text
            except (ValueError, IndexError):
                continue

    result = []
    for i, seg in enumerate(segments):
        translated = translated_lines.get(i, seg["text"])  # fallback ke original
        result.append({**seg, "translated_text": translated})

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3A: TTS dengan ElevenLabs (Primary)
# ─────────────────────────────────────────────────────────────────────────────

def tts_elevenlabs(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    """
    Generate audio dari teks menggunakan ElevenLabs API.
    Return path ke file audio jika berhasil, None jika gagal.
    """
    if not ELEVENLABS_API_KEY:
        return None

    voice_id = ELEVENLABS_VOICES.get(lang, ELEVENLABS_VOICES["default"])
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        if not output_path:
            tmp = tempfile.mktemp(suffix=".mp3")
            output_path = tmp

        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path

    except requests.RequestException as e:
        print(f"[Dubbing] ElevenLabs TTS error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3B: TTS dengan gTTS (Fallback gratis)
# ─────────────────────────────────────────────────────────────────────────────

def tts_gtts_fallback(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    """Google Text-to-Speech fallback (gratis, kualitas sedang)."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp3")
        tts.save(output_path)
        return output_path
    except Exception as e:
        print(f"[Dubbing] gTTS fallback error: {e}")
        return None


def generate_tts(text: str, lang: str = "id", output_path: str = "") -> Optional[str]:
    """Coba ElevenLabs dulu, fallback ke gTTS."""
    result = tts_elevenlabs(text, lang, output_path)
    if result:
        return result
    print("[Dubbing] ElevenLabs tidak tersedia, fallback ke gTTS...")
    return tts_gtts_fallback(text, lang, output_path)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Merge audio dub ke video menggunakan FFmpeg
# ─────────────────────────────────────────────────────────────────────────────

def _get_audio_duration(audio_path: str) -> float:
    """Dapatkan durasi file audio dalam detik."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def merge_dub_to_video(
    video_path: str,
    dubbed_audio_path: str,
    output_path: str,
    original_vol: float = 0.1,
) -> Optional[str]:
    """
    Gabungkan audio dub ke video:
    - Auto-adjust speed audio agar sinkron dengan durasi video
    - Keep original audio sangat pelan (0.1) sebagai ambient

    Args:
        video_path: Path video input
        dubbed_audio_path: Path audio hasil TTS
        output_path: Path video output
        original_vol: Volume audio asli (0.0 = mute total, 0.1 = sangat pelan)
    """
    import ffmpeg

    print(f"[Dubbing] Step 4: Merging dubbed audio ke video...")

    try:
        video_probe = ffmpeg.probe(video_path)
        vid_duration = float(video_probe["format"]["duration"])
        dub_duration = _get_audio_duration(dubbed_audio_path)

        # Hitung speed ratio untuk sync
        if dub_duration > 0 and abs(dub_duration - vid_duration) > 0.5:
            speed_ratio = dub_duration / vid_duration
            # Batasi di range wajar 0.7x - 1.5x
            speed_ratio = max(0.7, min(1.5, speed_ratio))
            atempo_filter = f"atempo={1/speed_ratio:.3f}"
            print(f"[Dubbing]   Speed adjust: {speed_ratio:.2f}x (dub={dub_duration:.1f}s, vid={vid_duration:.1f}s)")
        else:
            atempo_filter = None

        # Build FFmpeg graph
        video_in  = ffmpeg.input(video_path)
        dubbed_in = ffmpeg.input(dubbed_audio_path)
        original_audio = video_in.audio

        # Apply speed adjustment ke dub
        dub_stream = dubbed_in.audio
        if atempo_filter:
            dub_stream = dub_stream.filter("atempo", atempo_filter.split("=")[1])

        # Mix: dub loud + original quiet
        if original_vol > 0:
            orig_quiet = original_audio.filter("volume", original_vol)
            mixed_audio = ffmpeg.filter([dub_stream, orig_quiet], "amix", inputs=2, duration="first")
        else:
            mixed_audio = dub_stream

        # Output
        (
            ffmpeg.output(
                video_in.video,
                mixed_audio,
                output_path,
                vcodec="copy",  # Copy video stream, tidak re-encode (cepat!)
                acodec="aac",
                audio_bitrate="128k",
                shortest=None,
            )
            .overwrite_output()
            .run(quiet=True)
        )
        print(f"[Dubbing] Selesai: {output_path}")
        return output_path

    except Exception as e:
        print(f"[Dubbing] FFmpeg merge error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA: Full Dubbing Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def dub_video_clip(
    video_path: str,
    target_lang: str = "id",
    output_path: str = "",
    keep_original_audio: float = 0.1,
) -> Optional[str]:
    """
    Pipeline dubbing lengkap dari satu video klip.

    Args:
        video_path: Path video input (sudah dirender, format 9:16)
        target_lang: 'id' untuk Indonesia, 'en' untuk English
        output_path: Path output; jika kosong, akan digenerate otomatis
        keep_original_audio: 0.0 = mute original, 0.1 = ambient, 1.0 = full

    Returns:
        Path ke video dengan audio dubbing, atau None jika gagal
    """
    # Validasi
    if not os.path.exists(video_path):
        print(f"[Dubbing] Video tidak ditemukan: {video_path}")
        return None

    if not GROQ_API_KEY:
        print("[Dubbing] GROQ_API_KEY belum dikonfigurasi.")
        return None

    lang_name = "Indonesia" if target_lang == "id" else "English"
    print(f"\n[Dubbing] Memulai dubbing ke {lang_name} untuk: {os.path.basename(video_path)}")

    # Auto-generate output path
    if not output_path:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_dubbed_{target_lang}.mp4"

    # Ekstrak audio dari video
    temp_audio = tempfile.mktemp(suffix=".mp3")
    temp_dub   = tempfile.mktemp(suffix=".mp3")

    try:
        import ffmpeg as _ffmpeg
        print("[Dubbing] Mengekstrak audio dari video...")
        (
            _ffmpeg.input(video_path)
            .output(temp_audio, acodec="libmp3lame", qscale=2)
            .overwrite_output()
            .run(quiet=True)
        )

        # STEP 1: Transkripsi
        segments = transcribe_with_segments(temp_audio)
        if not segments:
            print("[Dubbing] Tidak ada segmen transkripsi ditemukan.")
            return None

        # STEP 2: Translate
        translated_segs = translate_segments(segments, target_lang)

        # Gabungkan semua teks terjemahan
        full_dubbed_text = " ".join(s["translated_text"] for s in translated_segs)
        print(f"[Dubbing] Teks dubbing ({len(full_dubbed_text)} karakter): {full_dubbed_text[:100]}...")

        # STEP 3: Generate TTS
        dub_audio = generate_tts(full_dubbed_text, target_lang, temp_dub)
        if not dub_audio:
            print("[Dubbing] TTS gagal dihasilkan.")
            return None

        # STEP 4: Merge ke video
        result = merge_dub_to_video(
            video_path=video_path,
            dubbed_audio_path=dub_audio,
            output_path=output_path,
            original_vol=keep_original_audio,
        )
        return result

    finally:
        # Cleanup temp files
        for f in [temp_audio, temp_dub]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass
