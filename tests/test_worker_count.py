"""Jumlah worker Taskiq mengikuti inti fisik (min 1, genap untuk 2+ core)."""

from backend.core import worker_count as wc


def test_even_recommendation_from_physical_cores(monkeypatch):
    monkeypatch.delenv("TASKIQ_WORKERS", raising=False)
    for cores, expected in [(1, 1), (2, 2), (3, 4), (4, 4), (5, 6), (6, 6), (8, 8)]:
        monkeypatch.setattr(wc, "physical_cores", lambda value=cores: value)
        assert wc.recommended_workers() == expected


def test_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("TASKIQ_WORKERS", "8")
    assert wc.recommended_workers() == 8
    assert wc.configured_workers() == 8

    monkeypatch.setenv("TASKIQ_WORKERS", "")
    assert wc.configured_workers() == 0
