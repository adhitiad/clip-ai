"""Guard: repo ini sengaja bebas model ML / artefak training."""

import asyncio
from pathlib import Path

import backend.services.viral_predictor as predictor
from backend.main import app
from backend.routes.tools import model_status


def test_no_training_api_in_predictor():
    for name in (
        "train_model",
        "save_training_sample",
        "_load_training_data",
        "_load_model",
        "_save_model",
        "MODEL_PATH",
        "SCALER_PATH",
        "DATA_PATH",
        "RETRAIN_EVERY",
    ):
        assert not hasattr(predictor, name), name


def test_no_pickle_or_training_data_files():
    root = Path(__file__).resolve().parents[1]
    for pattern in ("**/*.pkl", "**/training_data.jsonl"):
        # uv-tools berisi dependency scanner pihak ketiga, bukan artefak model.
        excluded = {".venv", "__pycache__", "uv-tools"}
        matches = [
            path for path in root.glob(pattern) if not excluded.intersection(path.parts)
        ]
        assert not matches, matches


def test_no_retrain_route():
    paths = set(app.openapi()["paths"])
    assert "/dashboard/godsmode/retrain-viral-model" not in paths


def test_model_status_reports_rule_based():
    result = asyncio.run(model_status())
    assert result["model"]["enabled"] is False
    assert result["model"]["confidence_mode"] == "rule_based"
