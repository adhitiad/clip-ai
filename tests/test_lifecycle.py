"""Lifecycle data pribadi: audit AI, ekspor, dan hapus dengan konfirmasi."""

from fastapi.testclient import TestClient

from backend.core import audit
from backend.core.auth import get_current_active_user, get_db
from backend.main import app
from backend.models.clip import Clip
from backend.models.feedback import PerformanceFeedbackRecord

USER = type("User", (), {"id": 1, "email": "owner@example.com", "username": "owner"})()


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None

    def delete(self):
        count = len(self.rows)
        self.rows.clear()
        return count


class FakeDB:
    def __init__(self):
        self.rows = {}

    def query(self, model):
        return FakeQuery(self.rows.setdefault(model, []))

    def commit(self):
        pass


def test_audit_log_writes_and_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_PATH", tmp_path / "audit.jsonl")
    record = audit.log_ai_call("llm", "nvidia", "model-x", success=True)
    assert record["kind"] == "llm"
    assert record["provider"] == "nvidia"
    assert "api_key" not in record
    assert audit.read_audit(5)[0]["model"] == "model-x"


def test_export_and_confirmed_delete():
    fake = FakeDB()
    fake.rows[Clip] = [Clip(id=1, title_en="Judul")]
    fake.rows[PerformanceFeedbackRecord] = [
        PerformanceFeedbackRecord(clip_id=1, predicted_score=7.0, real_score=8.0)
    ]
    app.dependency_overrides[get_current_active_user] = lambda: USER
    app.dependency_overrides[get_db] = lambda: fake
    try:
        with TestClient(app) as client:
            exported = client.get("/ops/export")
            assert exported.status_code == 200
            assert len(exported.json()["clips"]) == 1
            assert len(exported.json()["feedback"]) == 1

            rejected = client.request("DELETE", "/ops/data", json={"confirm": "salah"})
            assert rejected.status_code == 400
            assert fake.rows[Clip]

            removed = client.request("DELETE", "/ops/data", json={"confirm": "DELETE"})
            assert removed.status_code == 200
            assert not fake.rows[Clip]
            assert not fake.rows[PerformanceFeedbackRecord]
    finally:
        app.dependency_overrides.clear()


def test_audit_endpoint_maps_records(monkeypatch):
    from backend.routes import ops as ops_routes

    monkeypatch.setattr(
        ops_routes,
        "read_audit",
        lambda _limit: [
            {
                "timestamp": "2026-11-25T00:00:00+00:00",
                "kind": "llm",
                "provider": "nvidia",
                "model": "model-x",
                "success": True,
                "request_id": "req-1",
                "trace_id": "trace-1",
                "span_id": "span-1",
            }
        ],
    )
    app.dependency_overrides[get_current_active_user] = lambda: USER
    try:
        with TestClient(app) as client:
            response = client.get("/ops/audit")
            assert response.status_code == 200
            assert response.json()[0]["kind"] == "llm"
            assert response.json()[0]["span_id"] == "span-1"
    finally:
        app.dependency_overrides.clear()
