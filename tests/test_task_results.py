"""Result backend Taskiq — cache memori + persistensi via SessionLocal."""

import asyncio
from types import SimpleNamespace

from taskiq import TaskiqResult
from taskiq.depends.progress_tracker import TaskProgress, TaskState

from backend.core import task_results as tr


class FakeDB:
    rows: dict[str, object] = {}

    def get(self, _model, task_id):
        return self.rows.get(task_id)

    def add(self, row):
        self.rows[row.task_id] = row

    def commit(self):
        pass

    def close(self):
        pass


def _fake_row(task_id):
    return SimpleNamespace(
        task_id=task_id,
        status="PENDING",
        result_json=None,
        error=None,
        progress_current=0,
        progress_total=0,
        attempts=0,
    )


def test_result_backend_persists_progress_and_result(monkeypatch):
    FakeDB.rows.clear()
    tr._cache.clear()
    monkeypatch.setattr(tr, "SessionLocal", lambda: FakeDB())

    backend = tr.PostgresResultBackend()
    asyncio.run(
        backend.set_progress(
            "task-1",
            TaskProgress(state=TaskState.STARTED, meta={"current": 1, "total": 2}),
        )
    )
    snapshot = tr.get_task_snapshot("task-1")
    assert snapshot["status"] == "PROGRESS"
    assert snapshot["progress"]["percent"] == 50

    asyncio.run(
        backend.set_result(
            "task-1",
            TaskiqResult(
                is_err=False,
                log=None,
                return_value={"files": ["a.mp4"]},
                execution_time=0.1,
                labels={},
                error=None,
            ),
        )
    )
    snapshot = tr.get_task_snapshot("task-1")
    assert snapshot["status"] == "SUCCESS"
    assert snapshot["result"] == {"files": ["a.mp4"]}
    assert asyncio.run(backend.is_result_ready("task-1")) is True


def test_snapshot_fallback_when_no_row(monkeypatch):
    FakeDB.rows.clear()
    tr._cache.clear()
    monkeypatch.setattr(tr, "SessionLocal", lambda: FakeDB())
    assert tr.get_task_snapshot("missing")["status"] == "PENDING"
