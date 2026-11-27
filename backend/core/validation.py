"""Validasi input & path untuk project pribadi (T-11).

Semua helper murni, mudah di-test, tanpa bergantung pada request FastAPI.
"""

import re
import unicodedata
from pathlib import Path

MAX_SCRIPT_TEXT = 5000
MAX_TOPIC = 300
MAX_QUERY = 200
ALLOWED_LANGS = {"id", "en"}
ALLOWED_SEARCH_TYPES = {
    "auto",
    "fast",
    "deep-lite",
    "deep",
    "deep-reasoning",
    "instant",
}


def sanitize_filename(name: str, fallback: str = "clip") -> str:
    """Nama file aman dari output AI/LLM (tanpa path separator, tanpa BOM)."""
    cleaned = unicodedata.normalize("NFKD", str(name)).lstrip("\ufeff")
    cleaned = "".join(char for char in cleaned if not unicodedata.combining(char))
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned).strip("._-")
    return (cleaned or fallback)[:120]


def is_within_root(path: Path, root: Path) -> bool:
    """PATH traversal guard: pastikan path berada di dalam root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError, OSError:
        return False


def resolve_confined_path(value: str, root: Path) -> Path:
    """Resolve path milik user dan pastikan tidak keluar dari root."""
    path = Path(value).expanduser().resolve()
    if not is_within_root(path, root):
        raise ValueError(f"Path harus berada di dalam {root}")
    return path


def validate_lang(lang: str) -> str:
    normalized = str(lang).strip().lower()
    if normalized not in ALLOWED_LANGS:
        raise ValueError(f"Bahasa harus salah satu dari {sorted(ALLOWED_LANGS)}")
    return normalized


def validate_search_type(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in ALLOWED_SEARCH_TYPES:
        raise ValueError(
            f"search_type harus salah satu dari {sorted(ALLOWED_SEARCH_TYPES)}"
        )
    return normalized


def validate_text(value: str, field: str, max_length: int, min_length: int = 1) -> str:
    text = str(value).strip().lstrip("\ufeff")
    if len(text) < min_length:
        raise ValueError(f"{field} tidak boleh kosong")
    if len(text) > max_length:
        raise ValueError(f"{field} maksimal {max_length} karakter")
    return text
