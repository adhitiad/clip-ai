"""Pipeline render yang dipakai worker Taskiq, CLI `render_job.py`, dan worker AMQP."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from backend.services.render_cache import compute_job_key, lookup_cached, record_cached


def _concat_parts(parts: list[str], output_path: str) -> str | None:
    """Gabung bagian MP4 (codec seragam) jadi satu file via FFmpeg concat."""
    from backend.log import logger

    if not parts:
        return None
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if len(parts) == 1:
        os.replace(parts[0], output_path)
        return output_path

    list_path = f"temp/concat_{Path(output_path).stem}.txt"
    os.makedirs(os.path.dirname(list_path) or ".", exist_ok=True)
    with open(list_path, "w", encoding="utf-8") as handle:
        for part in parts:
            handle.write(f"file '{Path(part).resolve().as_posix()}'\n")

    base = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
    ]
    try:
        subprocess.run(
            [*base, "-c", "copy", output_path],
            check=True,
            capture_output=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(
            f"[Render] concat copy gagal ({type(exc).__name__}); re-encode bagian."
        )
        try:
            subprocess.run(
                [
                    *base,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-c:a",
                    "aac",
                    output_path,
                ],
                check=True,
                capture_output=True,
                timeout=900,
            )
        except (OSError, subprocess.SubprocessError) as exc2:
            logger.error(f"[Render] concat mix gagal: {type(exc2).__name__}")
            return None
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass
    return output_path if os.path.exists(output_path) else None


def render_clips(
    video_url: str,
    clips_metadata: list,
    lang: str,
    progress: Callable[[int, int], None] | None = None,
    mix: bool = False,
) -> dict:
    """Render semua klip; return ringkasan dengan manifest/cache info.

    ``mix=True`` merender tiap klip dari ``clip["source_url"]`` lalu
    menggabungkannya menjadi satu MP4.
    """
    from backend.log import logger
    from backend.services.video_engine import process_clip
    from backend.utils.youtube import download_video_segment

    total = len(clips_metadata)
    key = compute_job_key(video_url, clips_metadata, lang)
    cached = lookup_cached(key)
    if cached:
        logger.info(
            f"♻️ Render dilewati (cache hit {key[:12]}): {len(cached['files'])} file"
        )
        if progress:
            progress(total, total)
        thumbnails = [
            clip.get("thumbnail_url")
            for clip in (cached.get("clips_metadata") or [])
            if clip.get("thumbnail_url")
        ]
        return {
            "status": "success",
            "cached": True,
            "cache_key": key,
            "rendered_clips_count": total,
            "total_variants_generated": len(cached["files"]),
            "files": cached["files"],
            "thumbnails": thumbnails,
            "mix": mix,
        }

    files: list[str] = []
    parts: list[str] = []
    thumbnails: list[str] = []
    for index, clip in enumerate(clips_metadata):
        source_url = clip.get("source_url") or video_url
        logger.info(
            f"Taskiq Worker -> Persiapan render klip {index + 1}/{total}: "
            f"{clip.get('title_en')} ({clip.get('start_time')}s - {clip.get('end_time')}s)"
        )
        if mix:
            part_path = f"temp/mix_{key[:8]}_{index + 1}.mp4"
            variant = process_clip(
                source_url,
                clip,
                index + 1,
                download_video_segment,
                output_path=part_path,
            )
            if variant:
                parts.append(variant)
        else:
            variant = process_clip(source_url, clip, index + 1, download_video_segment)
            if variant:
                files.append(variant)
        thumb = clip.get("thumbnail_url")
        if thumb:
            thumbnails.append(thumb)
        if progress:
            progress(index + 1, total)

    if mix:
        raw_title = (
            clips_metadata[0].get("title_en", "mix") if clips_metadata else "mix"
        )
        safe_title = (
            "".join(c for c in raw_title if c.isalnum() or c == " ")
            .strip()
            .replace(" ", "_")[:60]
            or "mix"
        )
        output_path = f"output/MIX_{safe_title}_{key[:6]}.mp4"
        mixed = _concat_parts(parts, output_path) if parts else None
        if mixed:
            files = [mixed]
            for part in parts:
                try:
                    os.remove(part)
                except OSError:
                    pass

    entry = record_cached(key, files, clips_metadata=clips_metadata)
    return {
        "status": "success" if files else "partial",
        "cached": False,
        "cache_key": key,
        "rendered_clips_count": total,
        "total_variants_generated": len(files),
        "files": files,
        "thumbnails": thumbnails,
        "manifest": entry,
        "mix": mix,
    }
