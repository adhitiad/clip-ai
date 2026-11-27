"""GET /tasks/{task_id}: status + progres render (Taskiq result backend)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import backend.routes.tasks as tasks_route
from backend.core.auth import get_current_active_user
from backend.main import app

USER = SimpleNamespace(id=1, email="owner@example.com")


def _get(client: TestClient, task_id: str = "task-1"):
    app.dependency_overrides[get_current_active_user] = lambda: USER
    try:
        return client.get(f"/tasks/{task_id}")
    finally:
        app.dependency_overrides.clear()


def test_task_progress(monkeypatch):
    monkeypatch.setattr(
        tasks_route,
        "get_task_snapshot",
        lambda task_id: {
            "task_id": task_id,
            "status": "PROGRESS",
            "progress": {"current": 2, "total": 4, "percent": 50},
            "result": None,
            "error": None,
        },
    )
    with TestClient(app) as client:
        response = _get(client)

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-1"
    assert data["status"] == "PROGRESS"
    assert data["progress"] == {"current": 2, "total": 4, "percent": 50}


def test_task_success_has_no_progress(monkeypatch):
    monkeypatch.setattr(
        tasks_route,
        "get_task_snapshot",
        lambda task_id: {
            "task_id": task_id,
            "status": "SUCCESS",
            "progress": None,
            "result": {"files": ["out.mp4"]},
            "error": None,
        },
    )
    with TestClient(app) as client:
        response = _get(client)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["progress"] is None
    assert data["result"]["files"] == ["out.mp4"]
