"""Content intelligence: analisis video, brief LLM, trend, dan skor viral.

Dipakai worker RabbitMQ lewat ``backend/scripts/render_job.py``. Import berat
sengaja dilakukan di dalam fungsi agar CLI tetap ringan saat startup.
"""

import os
import re


def sanitize_terms(terms: object, limit: int = 5) -> list[str]:
    """Bersihkan keyword tren; perlakukan sebagai data, bukan instruksi."""
    if not isinstance(terms, list):
        return []
    cleaned = []
    for term in terms[:limit]:
        text = re.sub(r"[\x00-\x1f\x7f]", "", str(term)).strip()[:80]
        if text:
            cleaned.append(text)
    return cleaned


def analyze_video(video_url: str, topic: str, lang: str) -> list[dict]:
    """Transkrip/audio + LLM hook → timing klip asli dari video."""
    from backend.core.ai_pipeline import process_video_ai_logic
    from backend.utils.youtube import check_and_get_youtube_subs, download_audio_only

    transcript = check_and_get_youtube_subs(video_url, lang) or ""
    audio_path = "" if transcript else download_audio_only(video_url)
    try:
        return process_video_ai_logic(
            audio_path=audio_path,
            user_query=topic,
            transcript_text=transcript,
        )
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


def apply_brief_to_clips(
    clips: list[dict],
    brief: dict | None,
    target_language: str = "id",
    trend_terms: list[str] | None = None,
) -> list[dict]:
    """Gabungkan timing asli dengan copy brief LLM + keyword tren."""
    planned = (brief or {}).get("clips") or []
    for index, clip in enumerate(clips):
        if index >= len(planned):
            break
        item = planned[index]
        title = str(item.get("title") or f"Clip {index + 1}")
        hook = str(item.get("hook") or "")
        caption = str(item.get("caption") or "")
        hashtags = item.get("hashtags") or []
        parts = [hook, caption, *[str(tag) for tag in hashtags]]
        if trend_terms:
            parts.extend(trend_terms[:3])
        desc = " ".join(part for part in parts if part).strip()
        clip.update(
            {
                "title_id": title,
                "title_en": title,
                "desc_id": desc,
                "desc_en": desc,
                "hook": hook,
                "agent_hashtags": hashtags,
                "target_language": target_language,
            }
        )
    return clips


def score_clips(clips: list[dict], threshold: float | None = None) -> list[dict]:
    """Lampirkan skor viral rule-based ke tiap klip."""
    from backend.services.viral_predictor import predict_viral_score

    scored = []
    for clip in clips:
        scored.append(predict_viral_score(clip_metadata=clip, threshold=threshold))
    return scored
