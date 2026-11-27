"""CLI render_job: payload dari stdin → JSON hasil di stdout."""

import io
import json

from backend.scripts import render_job


def test_render_job_prints_result(monkeypatch):
    payload = {
        "video_url": "https://youtu.be/a",
        "clips": [{"title_en": "A", "start_time": 0, "end_time": 10}],
        "lang": "id",
        "request_id": "req-1",
        "traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(
        "backend.services.content_intelligence.analyze_video",
        lambda *args: [{"start_time": 0, "end_time": 10}],
    )
    monkeypatch.setattr(
        "backend.services.content_intelligence.score_clips",
        lambda clips, threshold=None: clips,
    )
    monkeypatch.setattr(
        "backend.services.render_pipeline.render_clips",
        lambda *args, **kwargs: {
            "status": "success",
            "cached": True,
            "files": ["a.mp4"],
        },
    )
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)

    assert render_job.main() == 0
    data = json.loads(output.getvalue())
    assert data["cached"] is True
    assert data["files"] == ["a.mp4"]
