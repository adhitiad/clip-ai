"""Gate kontrak hidup: OpenAPI, docs, dan .env.example tidak boleh drift."""

import json
import re
from pathlib import Path

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]

# Endpoint/jalur yang sudah dihapus; tidak boleh muncul sebagai key aktif.
STALE_ACTIVE_KEYS = {
    "OWNER_BOOTSTRAP_TOKEN",
    "HF_MODEL_REPO",
    "REDIS_PROVIDER",
    "REDIS_URL",
    "UPSTASH_REDIS_URL",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "REDISCLOUD_URL",
    "REDIS_SSL_CERT_REQS",
}

# Key minimum yang wajib ada di template agar setup bisa diikuti.
REQUIRED_KEYS = {
    "SECRET_KEY",
    "DATABASE_URL",
    "RABBITMQ_URL",
    "AGENT_PROVIDER",
    "AGENT_MODEL",
    "TTS_PROVIDER",
    "STT_PROVIDER",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "AUTH_BRIDGE_TOKEN",
    "OWNER_EMAILS",
}


def test_openapi_snapshot_matches_live_app():
    snapshot = json.loads((ROOT / "docs/openapi.json").read_text(encoding="utf-8"))
    live = app.openapi()

    assert snapshot.get("openapi") == live.get("openapi")
    assert snapshot.get("info") == live.get("info")
    assert set(snapshot.get("paths", {})) == set(live["paths"])

    snap_schemas = snapshot.get("components", {}).get("schemas", {})
    live_schemas = live.get("components", {}).get("schemas", {})
    assert set(snap_schemas) == set(live_schemas)
    for name, schema in live_schemas.items():
        assert snap_schemas[name] == schema, f"schema {name} berbeda dari snapshot"


def test_docs_api_lists_every_openapi_path():
    text = (ROOT / "docs/API.md").read_text(encoding="utf-8")
    for path in sorted(app.openapi()["paths"]):
        assert f"`{path}`" in text, f"docs/API.md belum menyebut `{path}`"


def test_env_example_has_no_stale_or_missing_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    active_keys = {
        match.group(1)
        for match in re.finditer(r"^([A-Z][A-Z0-9_]*)=(.*)$", text, re.MULTILINE)
    }

    assert not (active_keys & STALE_ACTIVE_KEYS), active_keys & STALE_ACTIVE_KEYS
    assert REQUIRED_KEYS <= active_keys, REQUIRED_KEYS - active_keys
