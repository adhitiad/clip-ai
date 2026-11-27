"""Trace context lintas API → worker → CLI, file log, dan OTLP opsional."""

import json

from backend.core import telemetry

TRACEPARENT = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"


def test_parse_traceparent():
    assert telemetry.parse_traceparent(TRACEPARENT) == ("a" * 32, "b" * 16)
    assert telemetry.parse_traceparent("invalid") is None


def test_trace_propagation_and_local_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parent = telemetry.start_trace(TRACEPARENT, "req-1")
    assert parent.trace_id == "a" * 32
    assert parent.parent_span_id == "b" * 16

    with telemetry.span("child", provider="nvidia") as child:
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert telemetry.current_traceparent().startswith(f"00-{parent.trace_id}-")

    lines = (tmp_path / "logs" / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert any(
        r["event"] == "span.start" and r["span_name"] == "child" for r in records
    )
    assert any(r["event"] == "span.end" and "duration_ms" in r for r in records)
    assert all(r["trace_id"] == parent.trace_id for r in records)


def test_otlp_export_when_endpoint_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector.local:4318")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr(telemetry.urllib.request, "urlopen", fake_urlopen)
    telemetry.start_trace()
    telemetry.log_event("http.request", path="/agent/shorts")

    assert captured["url"] == "http://collector.local:4318/v1/traces"
    spans = captured["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert spans[0]["name"] == "http.request"
    assert len(spans[0]["traceId"]) == 32
