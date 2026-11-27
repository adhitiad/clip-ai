"""Endpoint pendapatan platform + saran AI (tanpa network nyata)."""

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient

from backend.core.auth import get_current_active_user
from backend.core.models import RevenueSnapshot
from backend.main import app
from backend.routes import revenue as revenue_routes
from backend.services import revenue_advice as advice_module
from backend.utils import youtube_token as yt

USER = type("User", (), {"id": 1, "email": "owner@example.com", "username": "owner"})()

SNAPSHOTS = [
    RevenueSnapshot(
        platform="youtube",
        available=True,
        status="ok",
        amount=12.34,
        currency="USD",
        period_start="2026-10-29",
        period_end="2026-11-25",
        source="youtube-analytics/v2",
    ),
    RevenueSnapshot(
        platform="tiktok",
        available=False,
        status="endpoint_tidak_tersedia",
        amount=None,
        currency=None,
        period_start="2026-10-29",
        period_end="2026-11-25",
        source="tiktok-adapter",
        note="tidak ada API publik",
    ),
]


def _client(monkeypatch):
    monkeypatch.setattr(revenue_routes, "collect_revenue", lambda _days: SNAPSHOTS)
    app.dependency_overrides[get_current_active_user] = lambda: USER
    return TestClient(app)


def test_summary_endpoint(monkeypatch):
    with _client(monkeypatch) as client:
        response = client.get("/revenue/summary?days=30")
        assert response.status_code == 200
        body = response.json()
        assert body["days"] == 30
        assert body["total_available"] == 12.34
        assert [item["platform"] for item in body["platforms"]] == [
            "youtube",
            "tiktok",
        ]
        assert body["platforms"][1]["available"] is False
    app.dependency_overrides.clear()


def test_advice_endpoint(monkeypatch):
    monkeypatch.setattr(
        revenue_routes,
        "generate_advice",
        lambda _snapshots: {
            "status": "success",
            "provider": "nvidia",
            "model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
            "recommendations": ["Uji hook 3 detik pertama.", "Upload jam 19.00."],
            "generated_at": "2026-11-25T00:00:00+00:00",
            "note": "Saran AI.",
        },
    )
    with _client(monkeypatch) as client:
        response = client.get("/revenue/advice")
        assert response.status_code == 200
        assert response.json()["provider"] == "nvidia"
        assert len(response.json()["recommendations"]) == 2
    app.dependency_overrides.clear()


def test_resolve_target_follows_agent_env(monkeypatch):
    monkeypatch.delenv("REVENUE_AI_MODEL", raising=False)
    monkeypatch.setenv("AGENT_PROVIDER", "nvidia")
    monkeypatch.setenv("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    assert advice_module.resolve_target() == (
        "nvidia",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    )


def test_resolve_target_override_and_validation(monkeypatch):
    monkeypatch.setenv("REVENUE_AI_MODEL", "groq/llama-3.1-8b-instant")
    assert advice_module.resolve_target() == ("groq", "llama-3.1-8b-instant")

    monkeypatch.setenv("REVENUE_AI_MODEL", "tanpa-slash")
    with pytest.raises(advice_module.AdviceUnavailable):
        advice_module.resolve_target()


def test_generate_advice_uses_agent_model(monkeypatch):
    captured: dict = {}

    class FakeLLM:
        def invoke(self, _prompt):
            return type("R", (), {"content": "Uji hook 3 detik pertama."})()

    def fake_select(**kwargs):
        captured.update(kwargs)
        return FakeLLM()

    monkeypatch.delenv("REVENUE_AI_MODEL", raising=False)
    monkeypatch.setenv("AGENT_PROVIDER", "nvidia")
    monkeypatch.setenv("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    monkeypatch.setattr(advice_module, "select_chat_model", fake_select)

    result = advice_module.generate_advice(SNAPSHOTS)
    assert captured["provider"] == "nvidia"
    assert captured["model"] == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert result["provider"] == "nvidia"
    assert result["recommendations"] == ["Uji hook 3 detik pertama."]


def test_advice_unavailable_and_rate_limit(monkeypatch):
    def _unavailable(_snapshots):
        raise advice_module.AdviceUnavailable("OPENROUTER_API_KEY belum diset.")

    monkeypatch.setattr(revenue_routes, "generate_advice", _unavailable)
    with _client(monkeypatch) as client:
        assert client.get("/revenue/advice").status_code == 503
    app.dependency_overrides.clear()

    monkeypatch.setattr(
        revenue_routes,
        "check_rate_limit",
        lambda _key: (_ for _ in ()).throw(RuntimeError("Rate limit")),
    )
    with _client(monkeypatch) as client:
        assert client.get("/revenue/advice").status_code == 429
    app.dependency_overrides.clear()


def test_total_available_ignores_unavailable_and_other_currency():
    from backend.services.platform_revenue import total_available

    snapshots = SNAPSHOTS + [
        RevenueSnapshot(
            platform="eur",
            available=True,
            status="ok",
            amount=99.0,
            currency="EUR",
            period_start="2026-11-01",
            period_end="2026-11-25",
            source="test",
        )
    ]
    assert total_available(snapshots, "USD") == 12.34


def test_youtube_token_decrypt(tmp_path, monkeypatch):
    secret = "rahasia-panjang-32-karakter-minimum"
    token = {"access_token": "akses", "refresh_token": "segar", "scope": "analytics"}
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    iv = b"0" * 12
    cipher = AESGCM(key).encrypt(iv, json.dumps(token).encode(), None)
    tag, data = cipher[-16:], cipher[:-16]
    encrypted = ".".join(base64.b64encode(part).decode() for part in (iv, tag, data))
    path = tmp_path / "youtube_tokens.json"
    path.write_text(
        '{"version": 1, "encrypted": "' + encrypted + '"}', encoding="utf-8"
    )
    monkeypatch.setattr(yt, "TOKEN_PATH", path)
    monkeypatch.setenv("YOUTUBE_TOKEN_ENCRYPTION_KEY", secret)

    assert yt.load_token() == token


def test_unavailable_adapters_without_credentials(monkeypatch):
    from backend.services import platform_revenue as pr

    monkeypatch.setattr(pr, "load_token", lambda: None)
    monkeypatch.setattr(pr, "valid_access_token", lambda: None)
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)

    youtube = pr.youtube_revenue()
    assert youtube.available is False
    assert youtube.status == "oauth_belum_terhubung"
    assert pr.tiktok_revenue().available is False
    assert pr.meta_reels_revenue().available is False
