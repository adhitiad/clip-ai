"""Audit file log JSONL lokal (A09): pastikan tidak ada secret/JWT yang tercatat.

Dipakai di CI setelah scan ZAP. Tidak mengubah file; exit 1 bila ada temuan.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG_FILES = (ROOT / "logs" / "trace.jsonl", ROOT / "logs" / "audit.jsonl")

SENSITIVE_KEYS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
    "id_token",
    "bridge_token",
    "client_secret",
)

SECRET_PATTERNS = (
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),  # Google API key
    re.compile(r"nvapi-[A-Za-z0-9_-]{10,}"),  # NVIDIA NIM
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}"),  # Google OAuth secret
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),  # GitHub PAT
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style key
)


def _is_sensitive(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEYS)


def _walk(value: Any, path: str, findings: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            if _is_sensitive(str(key)):
                findings.append(f"{child}: kunci sensitif")
            _walk(item, child, findings)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f"{path}[{index}]", findings)
        return
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}: pola {pattern.pattern}")
                break


def audit() -> int:
    findings: list[str] = []
    lines_seen = 0

    for log_path in LOG_FILES:
        if not log_path.is_file():
            continue
        for number, raw in enumerate(
            log_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                continue
            lines_seen += 1
            try:
                record = json.loads(raw)
            except ValueError:
                for pattern in SECRET_PATTERNS:
                    if pattern.search(raw):
                        findings.append(
                            f"{log_path.name}:{number}: baris bukan JSON mengandung pola {pattern.pattern}"
                        )
                        break
                continue
            _walk(record, log_path.name, findings)

    if findings:
        print(f"Audit log GAGAL: {len(findings)} temuan")
        for finding in findings[:20]:
            print(f"  - {finding}")
        return 1

    print(f"Audit log OK: {lines_seen} baris, 0 secret/JWT")
    return 0


if __name__ == "__main__":
    raise SystemExit(audit())
