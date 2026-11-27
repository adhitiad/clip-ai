"""Kontrak allowlist scan ZAP terhadap snapshot OpenAPI."""

import json
from pathlib import Path

from scripts.zap_auth_scan import SAFE_PATHS


def test_safe_paths_exist_and_are_get():
    spec = json.loads(Path("docs/openapi.json").read_text(encoding="utf-8"))
    for path in SAFE_PATHS:
        assert path in spec["paths"], f"{path} tidak ada di docs/openapi.json"
        assert "get" in spec["paths"][path], f"{path} bukan operasi GET"
