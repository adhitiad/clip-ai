"""Trace context W3C + log JSON lokal + OTLP opsional.

Default: `logs/trace.jsonl` + console. Bila `OTEL_EXPORTER_OTLP_ENDPOINT`
diset, span juga dikirim ke endpoint tersebut (best-effort, tidak memblokir).
"""

import json
import os
import secrets
import time
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.core.mongo import collection as mongo_collection
from backend.core.rotating_jsonl import append_jsonl

_state: ContextVar[dict | None] = ContextVar("telemetry_state", default=None)


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str = ""

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    parts = (value or "").split("-")
    if len(parts) != 4 or parts[0] != "00":
        return None
    if len(parts[1]) != 32 or len(parts[2]) != 16:
        return None
    return parts[1], parts[2]


def start_trace(traceparent: str | None = None, request_id: str = "") -> TraceContext:
    parsed = parse_traceparent(traceparent)
    trace_id = parsed[0] if parsed else secrets.token_hex(16)
    parent = parsed[1] if parsed else ""
    ctx = TraceContext(trace_id, secrets.token_hex(8), parent)
    _state.set({"ctx": ctx, "request_id": request_id, "span": "root"})
    return ctx


def current_context() -> TraceContext:
    state = _state.get()
    if state is None:
        return start_trace()
    return state["ctx"]


def current_traceparent() -> str:
    return current_context().traceparent


def log_event(event: str, **fields: object) -> None:
    state = _state.get() or {}
    ctx = state.get("ctx") or current_context()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "trace_id": ctx.trace_id,
        "span_id": ctx.span_id,
        "parent_span_id": ctx.parent_span_id,
        "request_id": state.get("request_id", ""),
        "span": state.get("span", ""),
        **fields,
    }
    coll = mongo_collection("trace_logs")
    if coll is not None:
        try:
            coll.insert_one(record)
        except Exception:
            pass
    else:
        try:
            append_jsonl(Path("logs") / "trace.jsonl", record)
        except OSError:
            pass
    _emit_otlp(record)


@contextmanager
def span(name: str, **attributes: object):
    """Buka child span; otomatis log durasi & error."""
    parent_state = _state.get() or {
        "ctx": current_context(),
        "request_id": "",
        "span": "root",
    }
    parent = parent_state["ctx"]
    child = TraceContext(parent.trace_id, secrets.token_hex(8), parent.span_id)
    token = _state.set(
        {
            "ctx": child,
            "request_id": parent_state.get("request_id", ""),
            "span": name,
        }
    )
    started = time.time()
    log_event("span.start", span_name=name, **attributes)
    try:
        yield child
    except Exception as exc:
        log_event("span.error", span_name=name, error=str(exc), **attributes)
        raise
    finally:
        log_event(
            "span.end",
            span_name=name,
            duration_ms=round((time.time() - started) * 1000, 2),
            **attributes,
        )
        _state.reset(token)


def _emit_otlp(record: dict) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return
    ctx = record
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "clip-ai"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": ctx["trace_id"],
                                "spanId": ctx["span_id"],
                                "parentSpanId": ctx.get("parent_span_id", ""),
                                "name": record.get("span_name") or record["event"],
                                "startTimeUnixNano": int(time.time() * 1_000_000_000),
                                "endTimeUnixNano": int(time.time() * 1_000_000_000),
                                "status": {"code": 1},
                            }
                        ]
                    }
                ],
            }
        ]
    }
    try:
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/traces",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=1):
            pass
    except Exception:
        pass
