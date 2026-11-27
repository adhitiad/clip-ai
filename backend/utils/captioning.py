"""Captioning berbasis transkripsi REST (OpenAI/Groq), tanpa SDK vendor."""

from backend.core.transcription import transcribe_segments, transcribe_words


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_audio(audio_path: str, srt_output_path: str):
    """Buat file SRT dari segmen transkrip + sensor kata kasar."""
    segments = transcribe_segments(audio_path)

    from backend.utils.ai_extras import censor_text_and_get_ranges

    segments, mute_ranges = censor_text_and_get_ranges(segments)

    with open(srt_output_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(segments, start=1):
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            srt_file.write(f"{i}\n")
            srt_file.write(
                f"{format_timestamp(segment['start'])} --> "
                f"{format_timestamp(segment['end'])}\n"
            )
            srt_file.write(f"{text}\n\n")

    return srt_output_path, mute_ranges


def get_word_level_transcription(audio_path: str) -> list:
    """Kata-per-kata dengan timestamp untuk subtitle dinamis."""
    return transcribe_words(audio_path)
