"""Audit log lokal untuk setiap panggilan AI (tanpa secret)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.core.mongo import collection as mongo_collection
from backend.core.request_id import get_request_id
from backend.core.rotating_jsonl import append_jsonl
from backend.core.telemetry import current_context

AUDIT_PATH = Path("logs/audit.jsonl")


def log_ai_call(
    kind: str,
    provider: str,
    model: str = "",
    success: bool = True,
    **details: object,
) -> dict:
    """Tulis satu entri audit; gagal menulis tidak boleh menggagalkan AI."""
    try:
        context = current_context()
        trace_id = context.trace_id
        span_id = context.span_id
    except Exception:
        trace_id, span_id = "", ""

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "provider": provider,
        "model": model,
        "success": bool(success),
        "request_id": get_request_id(),
        "trace_id": trace_id,
        "span_id": span_id,
        **details,
    }
    coll = mongo_collection("audit_logs")
    if coll is not None:
        try:
            coll.insert_one(record)
        except Exception:
            pass
    else:
        try:
            append_jsonl(AUDIT_PATH, record)
        except OSError:
            pass
    return record


def read_audit(limit: int = 50) -> list[dict]:
    from backend.core.mongo import read_recent

    mongo_rows = read_recent("audit_logs", limit)
    if mongo_rows:
        return list(reversed(mongo_rows))
    if not AUDIT_PATH.exists():
        return []
    records = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records
