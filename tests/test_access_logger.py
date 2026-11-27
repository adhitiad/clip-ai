"""Access logger: format baris & klasifikasi heuristik (tanpa Mongo nyata)."""

from types import SimpleNamespace

from backend.services import access_logger as al


def test_format_line_matches_requested_format():
    record = {
        "level": "info",
        "actor": "hacker",
        "timestamp": "2026-11-26T14:30:00+00:00",
        "method": "POST",
        "path": "/auth/google",
        "status": 401,
        "ip": "203.0.113.9",
        "browser": "curl",
        "http_version": "1.1",
        "flag": "❌",
    }
    line = al.format_line(record)
    assert line.startswith("info - hacker - 2026-11-26 14:30:00 - ")
    assert "POST /auth/google 401 ip=203.0.113.9" in line
    assert line.endswith("flag ❌")


def test_classify_server_error():
    request = SimpleNamespace(
        url=SimpleNamespace(path="/agent/shorts"),
        headers={},
    )
    level, actor, flag = al._classify(request, 500, "", "1.2.3.4", "")
    assert (level, actor, flag) == ("error", "**", "🛑")


def test_classify_known_user(monkeypatch):
    request = SimpleNamespace(
        url=SimpleNamespace(path="/dashboard/stats"),
        headers={},
    )
    monkeypatch.setattr(al, "_is_known_ip", lambda ip: True)
    monkeypatch.setattr(al, "_mark_known_ip", lambda ip, email: None)
    monkeypatch.setattr(al, "_record_failure", lambda ip: 0)
    level, actor, flag = al._classify(
        request, 200, "owner@example.com", "1.2.3.4", "Mozilla/5.0"
    )
    assert (level, actor, flag) == ("info", "user", "✅")


def test_classify_hacker_foreign_ip_failed_auth(monkeypatch):
    request = SimpleNamespace(
        url=SimpleNamespace(path="/auth/google"),
        headers={},
    )
    monkeypatch.setattr(al, "_is_known_ip", lambda ip: False)
    monkeypatch.setattr(al, "_record_failure", lambda ip: 1)
    level, actor, flag = al._classify(request, 401, "", "203.0.113.9", "curl/8.0")
    assert (level, actor, flag) == ("info", "hacker", "❌")


def test_classify_public_health_ok(monkeypatch):
    request = SimpleNamespace(
        url=SimpleNamespace(path="/health/live"),
        headers={},
    )
    monkeypatch.setattr(al, "_is_known_ip", lambda ip: False)
    monkeypatch.setattr(al, "_record_failure", lambda ip: 0)
    level, actor, flag = al._classify(request, 200, "", "203.0.113.9", "Mozilla/5.0")
    assert (level, actor, flag) == ("info", "**", "✅")


def test_parse_user_agent():
    browser, device, _ = al._parse_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
    )
    assert browser == "Chrome"
    assert device == "Windows"
