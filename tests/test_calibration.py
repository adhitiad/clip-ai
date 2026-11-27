"""Kalibrasi rule-based: override bobot & laporan korelasi (tanpa ML)."""

from types import SimpleNamespace

import numpy as np

from backend.services import viral_predictor as vp


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def order_by(self, *_args):
        return self

    def limit(self, _limit):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def query(self, _model):
        return FakeQuery(self.rows)


def test_weight_override_valid_and_invalid(monkeypatch):
    monkeypatch.setenv("VIRAL_SCORE_WEIGHTS", ",".join(["1.0"] * 10))
    assert np.allclose(vp.resolve_score_weights(), np.ones(10))

    monkeypatch.setenv("VIRAL_SCORE_WEIGHTS", "1,2,3")
    assert np.allclose(vp.resolve_score_weights(), vp.DEFAULT_SCORE_WEIGHTS)

    monkeypatch.setenv("VIRAL_SCORE_WEIGHTS", "bukan,angka")
    assert np.allclose(vp.resolve_score_weights(), vp.DEFAULT_SCORE_WEIGHTS)


def test_calibration_report_correlation():
    rows = [
        SimpleNamespace(predicted_score=4.0, real_score=4.1),
        SimpleNamespace(predicted_score=6.0, real_score=6.2),
        SimpleNamespace(predicted_score=8.0, real_score=7.9),
    ]
    report = vp.calibration_report(db=FakeDB(rows))
    assert report["samples"] == 3
    assert report["correlation"] > 0.9
    assert report["mean_actual"] > 6.0
    assert len(report["buckets"]) == 3


def test_calibration_report_needs_two_samples():
    report = vp.calibration_report(
        db=FakeDB([SimpleNamespace(predicted_score=5.0, real_score=5.0)])
    )
    assert report["samples"] == 1
    assert report["correlation"] is None
