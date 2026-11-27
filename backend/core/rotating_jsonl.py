"""Penulis JSONL lokal dengan rotasi ukuran dan redaksi secret.

Dipakai telemetry (`trace.jsonl`) dan audit (`audit.jsonl`). Format satu baris
JSON tidak berubah; hanya nama file saat rotasi: `.1`, `.2`, ... `.N`.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any

SENSITIVE_PARTS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
)

_LOCKS: dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCK_GUARD:
        return _LOCKS.setdefault(key, threading.Lock())


def _limits() -> tuple[int, int]:
    try:
        max_bytes = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    except ValueError:
        max_bytes = 5 * 1024 * 1024
    try:
        backups = int(os.getenv("LOG_BACKUPS", "3"))
    except ValueError:
        backups = 3
    return max(1024, max_bytes), max(1, backups)


def _is_sensitive(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _rotate(path: Path, backups: int) -> None:
    for index in range(backups - 1, 0, -1):
        source = Path(f"{path}.{index}")
        if source.exists():
            source.replace(Path(f"{path}.{index + 1}"))
    if path.exists():
        path.replace(Path(f"{path}.1"))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Tulis satu record; rotasi dilakukan sebelum baris baru bila perlu."""
    line = json.dumps(_redact(record), ensure_ascii=False, default=str) + "\n"
    max_bytes, backups = _limits()
    with _lock_for(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if (
            path.exists()
            and path.stat().st_size + len(line.encode("utf-8")) > max_bytes
        ):
            _rotate(path, backups)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
