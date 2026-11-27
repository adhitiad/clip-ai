"""Health publik: liveness selalu 200, readiness mengikuti DB dan broker."""

from fastapi.testclient import TestClient

from backend.core.auth import get_current_active_user
from backend.main import app
from backend.routes import health as health_routes

USER = type("User", (), {"id": 1, "email": "owner@example.com", "username": "owner"})()


def test_live_endpoint():
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}


def test_ready_endpoint_monkeypatched(monkeypatch):
    monkeypatch.setattr(
        health_routes, "check_connection", lambda: {"ok": True, "provider": "rabbitmq"}
    )
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200


def test_ready_endpoint_fails_without_broker(monkeypatch):
    monkeypatch.setattr(
        health_routes, "check_connection", lambda: {"ok": False, "error": "down"}
    )
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503


def test_ops_health_detail():
    app.dependency_overrides[get_current_active_user] = lambda: USER
    try:
        with TestClient(app) as client:
            response = client.get("/ops/health")
            assert response.status_code == 200
            body = response.json()
            assert body["version"] == "0.1.0"
            assert "providers" in body
            assert "embeddings" in body
    finally:
        app.dependency_overrides.clear()
