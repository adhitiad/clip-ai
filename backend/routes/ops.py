"""Operasional: task, antrean, cache render, trace, dan enqueue manual."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.core.audit import read_audit
from backend.core.auth import get_current_active_user, get_db
from backend.core.rabbitmq_config import check_connection
from backend.core.request_id import get_request_id
from backend.core.task_results import _cache, get_task_snapshot
from backend.core.taskiq_config import dead_letter
from backend.core.telemetry import current_traceparent
from backend.models.clip import Clip
from backend.models.feedback import PerformanceFeedbackRecord
from backend.models.owner_setting import OwnerSetting
from backend.models.task_result import TaskResult
from backend.models.user_setting import UserSetting
from backend.services import provider_health
from backend.services.model_discovery import MODEL_CATALOG
from backend.services.render_cache import load_manifest, save_manifest

_STARTED_AT = time.time()

router = APIRouter(
    prefix="/ops",
    tags=["Operations"],
    dependencies=[Depends(get_current_active_user)],
)


class TaskOut(BaseModel):
    task_id: str
    status: str
    progress: dict | None = None
    result: dict | None = None
    error: str | None = None
    attempts: int = 0


class QueueOut(BaseModel):
    broker: dict
    counts: dict[str, int]
    dead_letter_queue: str
    retry_policy: dict


class WorkersOut(BaseModel):
    physical_cores: int
    recommended_workers: int
    configured_workers: int


class ExportOut(BaseModel):
    status: str
    generated_at: str
    version: int = 1
    clips: list[dict]
    feedback: list[dict]
    task_results: list[dict]
    settings: dict


class PurgeIn(BaseModel):
    confirm: str


class HealthDetailOut(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    database: bool
    broker: dict
    tasks: dict[str, int]
    dlq: str
    workers: dict[str, int]
    providers: list[dict]
    embeddings: dict


class AccessLogOut(BaseModel):
    timestamp: str
    level: str
    actor: str
    flag: str
    ip: str
    email: str = ""
    user_type: str = ""
    device_id: str = ""
    device_name: str = ""
    browser: str = ""
    http_version: str = ""
    method: str = ""
    path: str = ""
    status: int = 0
    keterangan: str = ""
    line: str = ""


class AuditOut(BaseModel):
    timestamp: str = ""
    kind: str = ""
    provider: str = ""
    model: str = ""
    success: bool = True
    request_id: str = ""
    trace_id: str = ""
    span_id: str = ""


class CacheEntryOut(BaseModel):
    cache_key: str
    files: list[str]
    created_at: str | None = None


class CacheInvalidateIn(BaseModel):
    cache_key: str | None = None
    all: bool = False


class TraceOut(BaseModel):
    event: str
    timestamp: str
    trace_id: str
    request_id: str | None = None


class RenderEnqueueIn(BaseModel):
    video_url: str
    clips: list[dict]
    lang: str = "id"


class TaskActionOut(BaseModel):
    status: str
    task_id: str


class CacheInvalidateOut(BaseModel):
    status: str
    removed: int


class RenderEnqueueOut(BaseModel):
    status: str
    task_id: str
    queued_at: str


class PurgeOut(BaseModel):
    status: str
    deleted: dict[str, int]


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(TaskResult)
    if status:
        query = query.filter(TaskResult.status == status)
    rows = query.order_by(TaskResult.updated_at.desc()).limit(limit).all()
    return [
        TaskOut(
            task_id=row.task_id,
            status=row.status,
            progress=get_task_snapshot(row.task_id).get("progress"),
            result=row.result_json,
            error=row.error,
            attempts=get_task_snapshot(row.task_id).get("attempts", 0),
        )
        for row in rows
    ]


@router.delete("/tasks/{task_id}", response_model=TaskActionOut)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    row = db.get(TaskResult, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan.")
    db.delete(row)
    db.commit()
    _cache.pop(task_id, None)
    return {"status": "success", "task_id": task_id}


@router.get("/queue", response_model=QueueOut)
def queue_status(db: Session = Depends(get_db)):
    counts = {
        str(row[0]): int(row[1])
        for row in db.query(TaskResult.status, func.count(TaskResult.task_id))
        .group_by(TaskResult.status)
        .all()
    }
    return QueueOut(
        broker=check_connection(),
        counts=counts,
        dead_letter_queue=dead_letter.name,
        retry_policy={"max_retries": 2, "delay_seconds": 3, "jitter": True},
    )


@router.get("/workers", response_model=WorkersOut)
def workers_info():
    from backend.core.worker_count import (
        configured_workers,
        physical_cores,
        recommended_workers,
    )

    return WorkersOut(
        physical_cores=physical_cores(),
        recommended_workers=recommended_workers(),
        configured_workers=configured_workers(),
    )


@router.get("/cache", response_model=list[CacheEntryOut])
def cache_list():
    return [
        CacheEntryOut(
            cache_key=key,
            files=entry.get("files") or [],
            created_at=entry.get("created_at"),
        )
        for key, entry in load_manifest().items()
    ]


@router.post("/cache/invalidate", response_model=CacheInvalidateOut)
def cache_invalidate(request: CacheInvalidateIn):
    manifest = load_manifest()
    if request.all:
        removed = len(manifest)
        manifest = {}
    elif request.cache_key and request.cache_key in manifest:
        removed = 1
        manifest.pop(request.cache_key, None)
    else:
        removed = 0
    save_manifest(manifest)
    return {"status": "success", "removed": removed}


@router.get("/traces", response_model=list[TraceOut])
def traces(limit: int = Query(20, ge=1, le=200)):
    import json

    from backend.core.mongo import read_recent

    mongo_rows = read_recent("trace_logs", limit)
    if mongo_rows:
        return [
            TraceOut(
                event=str(r.get("event", "")),
                timestamp=str(r.get("timestamp", "")),
                trace_id=str(r.get("trace_id", "")),
                request_id=r.get("request_id"),
            )
            for r in reversed(mongo_rows)
        ]

    path = Path("logs/trace.jsonl")
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    result = []
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        result.append(
            TraceOut(
                event=str(record.get("event", "")),
                timestamp=str(record.get("timestamp", "")),
                trace_id=str(record.get("trace_id", "")),
                request_id=record.get("request_id"),
            )
        )
    return result


@router.post("/render", response_model=RenderEnqueueOut)
async def enqueue_render(request: RenderEnqueueIn):
    from workers.worker import process_all_clips_task

    task = await process_all_clips_task.kiq(
        request.video_url,
        request.clips,
        request.lang,
        get_request_id(),
        current_traceparent(),
    )
    return {
        "status": "processing",
        "task_id": task.task_id,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


def _row_dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


@router.get("/export", response_model=ExportOut)
def export_data(db: Session = Depends(get_db)):
    """Ekspor seluruh data pribadi (clip, feedback, task, pengaturan)."""
    user_setting = db.query(UserSetting).first()
    owner_setting = db.query(OwnerSetting).first()
    return ExportOut(
        status="success",
        generated_at=datetime.now(timezone.utc).isoformat(),
        clips=[_row_dict(row) for row in db.query(Clip).all()],
        feedback=[_row_dict(row) for row in db.query(PerformanceFeedbackRecord).all()],
        task_results=[_row_dict(row) for row in db.query(TaskResult).all()],
        settings={
            "user": _row_dict(user_setting) if user_setting else None,
            "owner": _row_dict(owner_setting) if owner_setting else None,
        },
    )


@router.delete("/data", response_model=PurgeOut)
def delete_data(request: PurgeIn, db: Session = Depends(get_db)):
    """Hapus semua data pribadi; butuh konfirmasi eksplisit 'DELETE'."""
    if request.confirm != "DELETE":
        raise HTTPException(
            status_code=400, detail="Kirim {confirm: 'DELETE'} untuk menghapus data."
        )
    counts = {}
    for model in (
        PerformanceFeedbackRecord,
        Clip,
        TaskResult,
        UserSetting,
        OwnerSetting,
    ):
        counts[model.__tablename__] = db.query(model).delete()
    db.commit()
    _cache.clear()
    return {"status": "success", "deleted": counts}


@router.get("/access-log", response_model=list[AccessLogOut])
def access_log(
    limit: int = Query(100, ge=1, le=500),
    only_flagged: bool = Query(False, description="Hanya ⚠️/❌/🛑"),
):
    """Tail access log identitas per-request dari MongoDB."""
    from backend.services.access_logger import format_line, is_enabled, read_logs

    if not is_enabled():
        return []
    rows = read_logs(limit=limit, only_flagged=only_flagged)
    result: list[AccessLogOut] = []
    for row in rows:
        data = {
            key: row.get(key, "")
            for key in (
                "timestamp",
                "level",
                "actor",
                "flag",
                "ip",
                "email",
                "user_type",
                "device_id",
                "device_name",
                "browser",
                "http_version",
                "method",
                "path",
                "status",
            )
        }
        data["keterangan"] = (
            f"{data.get('method', '')} {data.get('path', '')} "
            f"{data.get('status', '')} ip={data.get('ip', '')}"
        )
        data["line"] = format_line(row)
        result.append(AccessLogOut(**data))
    return result


@router.get("/audit", response_model=list[AuditOut])
def audit_log(limit: int = Query(50, ge=1, le=500)):
    """Tail audit panggilan AI (LLM/TTS/STT), tanpa API key/JWT."""
    return [AuditOut(**entry) for entry in read_audit(limit)]


@router.get("/health", response_model=HealthDetailOut)
def health_detail(db: Session = Depends(get_db)):
    """Snapshot kesehatan detail untuk owner."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    tasks = {
        str(row[0]): int(row[1])
        for row in db.query(TaskResult.status, func.count(TaskResult.task_id))
        .group_by(TaskResult.status)
        .all()
    }

    from backend.core.worker_count import (
        configured_workers,
        physical_cores,
        recommended_workers,
    )

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    ollama_ok = False
    try:
        response = requests.get(f"{host}/api/tags", timeout=2)
        ollama_ok = response.status_code == 200
    except requests.RequestException:
        pass

    providers = [
        {"id": name, **provider_health.health_state(name)} for name in MODEL_CATALOG
    ]
    return HealthDetailOut(
        status="ok" if db_ok else "degraded",
        version="0.1.0",
        uptime_seconds=round(time.time() - _STARTED_AT, 1),
        database=db_ok,
        broker=check_connection(),
        tasks=tasks,
        dlq=dead_letter.name,
        workers={
            "physical_cores": physical_cores(),
            "recommended": recommended_workers(),
            "configured": configured_workers(),
        },
        providers=providers,
        embeddings={
            "provider": "ollama",
            "host": host,
            "reachable": ollama_ok,
            "pinecone": bool(os.getenv("PINECONE_API_KEY", "").strip()),
        },
    )
