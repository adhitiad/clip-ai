"""Endpoint coverage: semua fitur punya HTTP endpoint & respons valid."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.core.auth import get_current_active_user
from backend.main import app

USER = SimpleNamespace(id=1, email="owner@example.com", username="owner")


def _client():
    app.dependency_overrides[get_current_active_user] = lambda: USER
    return TestClient(app)


def test_all_feature_groups_have_endpoints():
    paths = set(app.openapi()["paths"])
    required = {
        "/auth/google",
        "/auth/me",
        "/health/live",
        "/health/ready",
        "/ops/health",
        "/agent/shorts",
        "/clips",
        "/clips/{clip_id}",
        "/dashboard/health",
        "/niche/trending",
        "/ops/cache",
        "/ops/queue",
        "/ops/traces",
        "/ops/workers",
        "/ops/export",
        "/ops/data",
        "/ops/audit",
        "/ops/render",
        "/settings/me",
        "/settings/owner",
        "/tasks/{task_id}",
        "/tools/viral-score",
        "/tools/calibration",
        "/revenue/summary",
        "/revenue/advice",
        "/youtube/search",
    }
    assert required <= paths, required - paths


def test_ops_and_settings_endpoints_respond():
    with _client() as client:
        assert client.get("/ops/queue").status_code == 200
        assert (
            client.get("/ops/queue").json()["dead_letter_queue"] == "shorts-render-dlq"
        )
        assert client.get("/ops/cache").status_code == 200
        assert client.get("/ops/traces").status_code == 200
        workers = client.get("/ops/workers")
        assert workers.status_code == 200
        assert workers.json()["recommended_workers"] >= 2
        settings = client.get("/settings/me")
        assert settings.status_code == 200
        assert settings.json()["user_id"] == 1
        owner = client.get("/settings/owner")
        assert owner.status_code == 200
        assert owner.json()["owner_user_id"] == 1
    app.dependency_overrides.clear()


def test_calibration_endpoint_responds():
    with _client() as client:
        response = client.get("/tools/calibration")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    app.dependency_overrides.clear()


def test_provider_catalog_has_health_and_cost():
    with _client() as client:
        response = client.get("/tools/providers")
        assert response.status_code == 200
        provider = response.json()["providers"][0]
        assert {"latency_hint", "cost_tier", "healthy"} <= set(provider)
    app.dependency_overrides.clear()


def test_clip_detail_responds():
    with _client() as client:
        assert client.get("/clips").status_code == 200
        assert client.get("/clips/999999").status_code == 404
    app.dependency_overrides.clear()
