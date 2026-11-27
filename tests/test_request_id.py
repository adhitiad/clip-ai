"""T-17: request ID lintas API → worker."""

from fastapi.testclient import TestClient

from backend.core.request_id import get_request_id, new_request_id, set_request_id
from backend.main import app


def test_request_id_helpers():
    rid = new_request_id()
    assert len(rid) == 36  # UUID string
    set_request_id(rid)
    assert get_request_id() == rid
    set_request_id("")
    assert get_request_id() == ""


def test_middleware_sets_and_echoes_request_id():
    with TestClient(app) as client:
        response = client.post(
            "/tools/viral-score",
            json={"title": "Halo", "start_time": 0, "end_time": 30},
        )
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) == 36


def test_middleware_honors_incoming_request_id():
    with TestClient(app) as client:
        response = client.get("/auth/me", headers={"X-Request-ID": "incoming-123"})
    assert response.headers["x-request-id"] == "incoming-123"


def test_worker_accepts_request_id():
    import inspect

    from workers.worker import process_all_clips_task

    signature = inspect.signature(process_all_clips_task.original_func)
    assert "request_id" in signature.parameters
