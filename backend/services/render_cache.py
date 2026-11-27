"""Render idempoten + manifest artefak (hash konten, tanpa model ML)."""

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Naikkan bila pipeline di backend/services/video_engine.py berubah.
ENGINE_VERSION = "1"
MANIFEST_NAME = "manifest.json"


def _canonical(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def compute_job_key(
    video_url: str, clips_metadata: list, lang: str, output_dir: str = "output"
) -> str:
    """Hash input render + provider + versi engine; output_dir tidak mempengaruhi key."""
    payload = {
        "video_url": video_url,
        "clips": clips_metadata,
        "lang": lang,
        "engine": ENGINE_VERSION,
        "providers": {
            "llm": os.getenv("AGENT_PROVIDER", ""),
            "model": os.getenv("AGENT_MODEL", ""),
            "tts": os.getenv("TTS_PROVIDER", ""),
            "stt": os.getenv("STT_PROVIDER", ""),
        },
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def manifest_path(output_dir: str = "output") -> Path:
    return Path(output_dir) / MANIFEST_NAME


def load_manifest(output_dir: str = "output") -> dict:
    path = manifest_path(output_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def save_manifest(data: dict, output_dir: str = "output") -> None:
    path = manifest_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def probe_file(path: str) -> dict:
    """Metadata MP4 via ffprobe; fallback bila ffprobe tidak tersedia."""
    file = Path(path)
    size_kb = round(file.stat().st_size / 1024, 1) if file.exists() else 0.0
    result = {
        "path": path,
        "duration": 0.0,
        "size_kb": size_kb,
        "video_codec": "",
        "width": 0,
        "height": 0,
    }
    try:
        output = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_name,codec_type,width,height",
                "-of",
                "json",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        info = json.loads(output.stdout)
        video = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        result.update(
            {
                "duration": round(float(info.get("format", {}).get("duration", 0)), 2),
                "video_codec": video.get("codec_name", ""),
                "width": int(video.get("width", 0)),
                "height": int(video.get("height", 0)),
            }
        )
    except OSError, subprocess.SubprocessError, ValueError, TypeError:
        pass
    return result


def lookup_cached(key: str, output_dir: str = "output") -> dict | None:
    """Kembalikan entri hanya bila semua file artefak masih ada."""
    entry = load_manifest(output_dir).get(key)
    if not isinstance(entry, dict):
        return None
    files = entry.get("files") or []
    if not files or any(not Path(name).is_file() for name in files):
        return None
    return entry


def record_cached(
    key: str,
    files: list,
    output_dir: str = "output",
    clips_metadata: list | None = None,
) -> dict:
    """Simpan entri artefak ke manifest secara atomik."""
    manifest = load_manifest(output_dir)
    entry = {
        "files": list(files),
        "artifacts": [probe_file(name) for name in files],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if clips_metadata is not None:
        entry["clips_metadata"] = clips_metadata
    manifest[key] = entry
    save_manifest(manifest, output_dir)
    return entry
