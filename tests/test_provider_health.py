"""Provider health/cost signals & auto-fallback."""

import pytest

from backend.services import model_discovery as md
from backend.services import provider_health as ph


@pytest.fixture(autouse=True)
def clean_health():
    ph.reset()
    yield
    ph.reset()


def test_failure_cooldown_and_reset():
    ph.reset()
    assert ph.is_healthy("nvidia")
    assert ph.record_failure("nvidia") is False
    assert ph.is_healthy("nvidia")
    assert ph.record_failure("nvidia") is True
    assert ph.is_healthy("nvidia") is False
    state = ph.health_state("nvidia")
    assert state["failures"] == 2
    assert state["retry_after"] > 0
    ph.record_success("nvidia")
    assert ph.is_healthy("nvidia") is True
    ph.reset()


def test_auto_fallback_skips_unhealthy_but_manual_wins(monkeypatch):
    monkeypatch.setattr(
        md, "discover_models", lambda: {"nvidia": ["m1"], "groq": ["m2"]}
    )
    monkeypatch.delenv("AGENT_PROVIDER", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    ph.reset()
    ph.record_failure("nvidia")
    ph.record_failure("nvidia")

    chosen, model = md.resolve_provider_model(None, None)
    assert chosen == "groq"
    assert model in md.MODEL_CATALOG["groq"]
    assert md.resolve_provider_model("nvidia", "m1") == ("nvidia", "m1")
    ph.reset()


def test_provider_metadata_fields():
    meta = md.provider_metadata("nvidia")
    assert meta["cost_tier"] == "free"
    assert meta["latency_hint"] == "cepat"
    assert meta["healthy"] is True
