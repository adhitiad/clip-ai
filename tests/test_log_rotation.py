"""Rotasi dan redaksi file JSONL lokal (trace/audit)."""

import json

from backend.core.rotating_jsonl import append_jsonl


def test_rotation_keeps_recent_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_MAX_BYTES", "512")
    monkeypatch.setenv("LOG_BACKUPS", "2")
    target = tmp_path / "logs" / "trace.jsonl"

    for index in range(30):
        append_jsonl(target, {"event": "tick", "index": index, "padding": "x" * 40})

    assert target.exists()
    assert (tmp_path / "logs" / "trace.jsonl.1").exists()
    records = [
        json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
    ]
    assert records[-1]["event"] == "tick"
    assert records[-1]["index"] == 29


def test_secrets_are_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_MAX_BYTES", "1048576")
    target = tmp_path / "logs" / "audit.jsonl"
    secret = "super-secret-value-123"

    append_jsonl(
        target,
        {
            "kind": "llm",
            "api_key": secret,
            "bridge_token": secret,
            "nested": {"GOOGLE_CLIENT_SECRET": secret, "safe": "ok"},
        },
    )

    raw = target.read_text(encoding="utf-8")
    assert secret not in raw
    record = json.loads(raw.strip())
    assert record["api_key"] == "***"
    assert record["bridge_token"] == "***"
    assert record["nested"]["GOOGLE_CLIENT_SECRET"] == "***"
    assert record["nested"]["safe"] == "ok"
