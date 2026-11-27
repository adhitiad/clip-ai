"""Koneksi MongoDB opsional (Atlas/eksternal) via MONGODB_URL.

Dipakai bersama oleh access logger, trace/audit log, dan task results.
Bila MONGODB_URL kosong, semua pemanggil otomatis fallback ke penyimpanan
lama (file JSONL / PostgreSQL). Koneksi gagal tidak pernah melempar exception
ke jalur bisnis.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from backend.core.env import load_env
from backend.log import logger

load_env("backend")

MONGODB_URL = os.getenv("MONGODB_URL", "").strip()
MONGODB_DB = os.getenv("MONGODB_DB", "clip_ai_access").strip() or "clip_ai_access"

_client: Any = None
_lock = threading.Lock()


def enabled() -> bool:
    """True hanya bila MONGODB_URL diset dan koneksi berhasil."""
    return bool(MONGODB_URL) and get_client() is not None


def get_client() -> Any:
    global _client
    if not MONGODB_URL:
        return None
    with _lock:
        if _client is None:
            try:
                from pymongo import MongoClient

                _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=1500)
                _client.admin.command("ping")
            except Exception as exc:
                logger.warning(f"[Mongo] tidak tersedia: {type(exc).__name__}")
                _client = None
        return _client


def collection(name: str) -> Any:
    """Return pymongo collection atau None bila tidak aktif."""
    client = get_client()
    if client is None:
        return None
    try:
        return client[MONGODB_DB][name]
    except Exception:
        return None


def read_recent(name: str, limit: int) -> list[dict]:
    """Baca `limit` dokumen terbaru dari koleksi, tanpa `_id`."""
    coll = collection(name)
    if coll is None:
        return []
    try:
        return list(coll.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
    except Exception:
        return []
