"""T-11: rate limit endpoint AI."""

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import get_current_active_user
from backend.core.rate_limit import check_rate_limit, reset_buckets
from backend.main import app
from backend.routes import tools as tools_routes

USER = type("User", (), {"id": 1, "email": "owner@example.com", "username": "owner"})()


def test_rate_limit_allows_then_blocks(monkeypatch):
    reset_buckets()
    monkeypatch.setenv("AI_RATE_LIMIT_PER_MINUTE", "2")
    check_rate_limit("test-bucket")
    check_rate_limit("test-bucket")
    with pytest.raises(RuntimeError, match="Rate limit"):
        check_rate_limit("test-bucket")
    reset_buckets()
    check_rate_limit("test-bucket")  # reset berhasil


def test_dub_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(
        tools_routes,
        "check_rate_limit",
        lambda _key: (_ for _ in ()).throw(RuntimeError("Rate limit terlampaui")),
    )
    app.dependency_overrides[get_current_active_user] = lambda: USER
    try:
        with TestClient(app) as client:
            response = client.post(
                "/tools/dub",
                json={"video_path": "../../etc/passwd", "script_text": "x"},
            )
        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
