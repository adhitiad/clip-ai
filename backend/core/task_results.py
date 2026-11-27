"""Result backend Taskiq: MongoDB bila MONGODB_URL diset,否则 PostgreSQL.

Cache memori tetap dipakai keduanya untuk akses cepat. Bila Mongo tidak
aktif/gagal, seluruh jalur kembali ke PostgreSQL seperti sebelumnya.
"""

import asyncio
import json
from collections import OrderedDict
from threading import Lock

from taskiq.abc.result_backend import AsyncResultBackend
from taskiq.depends.progress_tracker import TaskProgress, TaskState
from taskiq.result import TaskiqResult

from backend.core.mongo import collection as mongo_collection
from backend.models.task_result import TaskResult as TaskResultRow
from backend.utils.db import SessionLocal

CACHE_LIMIT = 256
_lock = Lock()
_cache: OrderedDict[str, dict] = OrderedDict()


def _snapshot(row: TaskResultRow) -> dict:
    progress = None
    if row.progress_total:
        progress = {
            "current": int(row.progress_current),
            "total": int(row.progress_total),
            "percent": round(int(row.progress_current) / int(row.progress_total) * 100),
        }
    return {
        "task_id": row.task_id,
        "status": row.status,
        "progress": progress,
        "result": row.result_json,
        "error": row.error,
        "attempts": int(getattr(row, "attempts", 0) or 0),
    }


TASK_COLLECTION = "task_results"


def _mongo_get(task_id: str) -> dict | None:
    coll = mongo_collection(TASK_COLLECTION)
    if coll is None:
        return None
    try:
        doc = coll.find_one({"task_id": task_id}, {"_id": 0})
        if not doc:
            return None
        doc.pop("updated_at", None)
        return doc
    except Exception:
        return None


def _mongo_put(task_id: str, snapshot: dict) -> bool:
    coll = mongo_collection(TASK_COLLECTION)
    if coll is None:
        return False
    try:
        from datetime import datetime, timezone

        coll.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    **snapshot,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        return True
    except Exception:
        return False


def _cache_put(task_id: str, snapshot: dict) -> None:
    with _lock:
        _cache[task_id] = snapshot
        _cache.move_to_end(task_id)
        while len(_cache) > CACHE_LIMIT:
            _cache.popitem(last=False)


def get_task_snapshot(task_id: str) -> dict:
    """Baca cache dulu, lalu PostgreSQL; fallback PENDING bila tidak ada."""
    with _lock:
        cached = _cache.get(task_id)
        if cached is not None:
            return dict(cached)

    mongo_doc = _mongo_get(task_id)
    if mongo_doc is not None:
        _cache_put(task_id, mongo_doc)
        return mongo_doc

    fallback = {
        "task_id": task_id,
        "status": "PENDING",
        "progress": None,
        "result": None,
        "error": None,
        "attempts": 0,
    }
    try:
        db = SessionLocal()
        try:
            row = db.get(TaskResultRow, task_id)
            if row is None:
                return fallback
            snapshot = _snapshot(row)
        finally:
            db.close()
    except Exception:
        return fallback

    _cache_put(task_id, snapshot)
    return snapshot


def set_progress_sync(task_id: str, current: int, total: int) -> None:
    """Dipakai task sync (render_pipeline) tanpa perlu await."""
    _persist(
        task_id,
        status="PROGRESS",
        progress_current=int(current),
        progress_total=int(total),
    )


def record_attempt(task_id: str, attempt: int) -> None:
    """Catat percobaan ke-N (label `_retries` dari middleware Taskiq)."""
    _persist(task_id, attempts=max(1, int(attempt)))


def _persist(task_id: str, **fields: object) -> dict:
    # Mongo dipakai lebih dulu bila aktif; kolom lama tetap dipetakan.
    current = _mongo_get(task_id) or get_task_snapshot(task_id)
    snapshot = dict(current)
    snapshot["task_id"] = task_id
    for key, value in fields.items():
        snapshot[_MONGO_FIELD_MAP.get(key, key)] = value

    if _mongo_put(task_id, snapshot):
        _cache_put(task_id, snapshot)
        return snapshot

    try:
        db = SessionLocal()
        try:
            row = db.get(TaskResultRow, task_id)
            if row is None:
                row = TaskResultRow(task_id=task_id)
                db.add(row)
            for key, value in fields.items():
                setattr(row, key, value)
            db.commit()
            snapshot = _snapshot(row)
        finally:
            db.close()
    except Exception:
        snapshot = {
            "task_id": task_id,
            "status": str(fields.get("status", "PENDING")),
            "progress": None,
            "result": fields.get("result_json"),
            "error": fields.get("error"),
            "attempts": int(fields.get("attempts", 0) or 0),
        }
    _cache_put(task_id, snapshot)
    return snapshot


_MONGO_FIELD_MAP = {"result_json": "result"}


class PostgresResultBackend(AsyncResultBackend[dict]):
    """Simpan hasil & progress task ke PostgreSQL, baca via cache memori."""

    async def set_result(self, task_id: str, result: TaskiqResult[dict]) -> None:
        value = result.return_value
        if not isinstance(value, dict):
            value = {"value": value}
        await asyncio.to_thread(
            _persist,
            task_id,
            status="FAILURE" if result.is_err else "SUCCESS",
            result_json=json.loads(json.dumps(value, default=str)),
            error=str(result.error) if result.error else None,
        )

    async def is_result_ready(self, task_id: str) -> bool:
        snapshot = await asyncio.to_thread(get_task_snapshot, task_id)
        return snapshot["status"] in {"SUCCESS", "FAILURE"}

    async def get_result(
        self, task_id: str, with_logs: bool = False
    ) -> TaskiqResult[dict]:
        snapshot = await asyncio.to_thread(get_task_snapshot, task_id)
        return TaskiqResult(
            is_err=snapshot["status"] == "FAILURE",
            log=None,
            return_value=snapshot.get("result") or {},
            execution_time=0.0,
            labels={},
            error=None,
        )

    async def set_progress(self, task_id: str, progress: TaskProgress) -> None:
        meta = progress.meta or {}
        await asyncio.to_thread(
            _persist,
            task_id,
            status="PROGRESS",
            progress_current=int(meta.get("current", 0)),
            progress_total=int(meta.get("total", 0)),
        )

    async def get_progress(self, task_id: str) -> TaskProgress | None:
        snapshot = await asyncio.to_thread(get_task_snapshot, task_id)
        if not snapshot.get("progress"):
            return None
        return TaskProgress(state=TaskState.STARTED, meta=snapshot["progress"])
