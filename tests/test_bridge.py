"""Bridge session frontend → JWT backend (dipakai UI shorts)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.core.auth import get_db
from backend.main import app
from backend.routes import bridge as bridge_routes


def test_bridge_issues_jwt_for_allowed_email(monkeypatch):
    monkeypatch.setenv("AUTH_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("OWNER_EMAILS", "owner@example.com")
    monkeypatch.setattr(bridge_routes, "router", bridge_routes.router)

    fake_user = SimpleNamespace(email="owner@example.com")

    class FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return fake_user

    class FakeDB:
        def query(self, _model):
            return FakeQuery()

    app.dependency_overrides[get_db] = lambda: FakeDB()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/bridge",
                json={
                    "email": "owner@example.com",
                    "bridge_token": "test-bridge-token",
                },
            )
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert len(response.json()["access_token"]) > 50
    finally:
        app.dependency_overrides.clear()


def test_bridge_provisions_missing_owner(monkeypatch):
    monkeypatch.setenv("AUTH_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("OWNER_EMAILS", "new-owner@example.com")

    created: dict = {}

    class FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, _model):
            return FakeQuery()

        def add(self, user):
            created["user"] = user

        def commit(self):
            created["committed"] = True

        def refresh(self, _user):
            pass

    app.dependency_overrides[get_db] = lambda: FakeDB()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/bridge",
                json={
                    "email": "new-owner@example.com",
                    "bridge_token": "test-bridge-token",
                },
            )
        assert response.status_code == 200
        assert created["committed"] is True
        assert created["user"].email == "new-owner@example.com"
        assert created["user"].hashed_password == bridge_routes.GOOGLE_PASSWORD_SENTINEL
    finally:
        app.dependency_overrides.clear()


def test_bridge_rejects_wrong_token_and_email(monkeypatch):
    monkeypatch.setenv("AUTH_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("OWNER_EMAILS", "owner@example.com")
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    try:
        with TestClient(app) as client:
            bad_token = client.post(
                "/auth/bridge",
                json={"email": "owner@example.com", "bridge_token": "salah"},
            )
            bad_email = client.post(
                "/auth/bridge",
                json={
                    "email": "stranger@example.com",
                    "bridge_token": "test-bridge-token",
                },
            )
        assert bad_token.status_code == 401
        assert bad_email.status_code == 401
    finally:
        app.dependency_overrides.clear()
