"""Google-only auth: tidak ada endpoint password."""

from fastapi.testclient import TestClient

from backend.core.auth import get_db
from backend.main import app
from backend.routes import auth as auth_routes


def test_no_password_endpoints(monkeypatch):
    paths = set(app.openapi()["paths"])
    assert "/auth/google" in paths
    assert "/auth/token" not in paths
    assert "/auth/register" not in paths


def test_google_login_creates_user(monkeypatch):
    class FakeQuery:
        def __init__(self, values):
            self.values = values

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.values[0] if self.values else None

    class FakeDB:
        def __init__(self):
            self.added = []

        def query(self, _model):
            return FakeQuery([None])

        def add(self, value):
            self.added.append(value)

        def commit(self):
            return None

        def refresh(self, value):
            return None

    fake_db = FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db
    monkeypatch.setattr(
        auth_routes,
        "verify_google_token",
        lambda _token: {
            "email": "adhitiadwima@gmail.com",
            "email_verified": True,
            "sub": "google-sub-123",
        },
    )
    try:
        with TestClient(app) as client:
            response = client.post("/auth/google", json={"id_token": "fake"})
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert fake_db.added
    finally:
        app.dependency_overrides.clear()
