"""T-12: API pribadi — auth Google, dashboard, YouTube."""

from fastapi.testclient import TestClient

from backend.core.auth import get_db
from backend.main import app
from backend.routes import auth as auth_routes


def test_google_login_rejects_email_outside_whitelist(monkeypatch):
    monkeypatch.setattr(auth_routes, "OWNER_EMAILS", {"owner@example.com"})
    monkeypatch.setattr(
        auth_routes,
        "verify_google_token",
        lambda _: {"email": "stranger@example.com", "email_verified": True, "sub": "x"},
    )
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.post("/auth/google", json={"id_token": "fake"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_private_dashboard_endpoints():
    paths = set(app.openapi()["paths"])
    assert "/dashboard/overview" in paths
    assert "/dashboard/stats" in paths
    assert "/dashboard/health" in paths
    assert not any("/dashboard/owner" in path or "godsmode" in path for path in paths)


def test_youtube_router_registered():
    paths = set(app.openapi()["paths"])
    assert "/youtube/search" in paths
    assert "/youtube/scheduler/status" in paths
    assert "/youtube/scheduler/collect" in paths


def test_youtube_scheduler_requires_cron_secret_and_jwt(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CRON_SECRET", "rahasia-cron")
    with TestClient(app) as client:
        assert client.get("/youtube/scheduler/status").status_code in (401, 503)
        assert client.post(
            "/youtube/scheduler/collect", json={"query": "x"}
        ).status_code in (401, 503)
        headers = {"x-cron-secret": "rahasia-cron"}
        assert (
            client.get("/youtube/scheduler/status", headers=headers).status_code == 401
        )


def test_protected_endpoints_require_auth():
    with TestClient(app) as client:
        for path in (
            "/auth/me",
            "/dashboard/overview",
            "/agent/shorts",
            "/niche/trending",
        ):
            response = (
                client.get(path)
                if path != "/agent/shorts"
                else client.post(path, json={"topic": "halo dunia"})
            )
            assert response.status_code in (401, 422), f"{path}: {response.status_code}"
