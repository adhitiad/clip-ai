"""Render lintas sumber: tiap klip dari videonya, lalu satu MP4 hasil mix."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

from backend.services import render_pipeline
from workers import worker as worker_module

CLIPS = [
    {
        "title_en": "Gol Detik Terakhir",
        "start_time": 0,
        "end_time": 10,
        "source_url": "https://youtu.be/a",
    },
    {
        "title_en": "Save Kiper",
        "start_time": 5,
        "end_time": 15,
        "source_url": "https://youtu.be/b",
    },
]


def test_render_clips_mix_uses_each_clip_source(monkeypatch):
    calls: list = []

    def fake_process(video_url, clip, index, download_func, output_path=None):
        calls.append((video_url, output_path))
        Path(output_path).write_bytes(b"part")
        return output_path

    monkeypatch.setattr("backend.services.video_engine.process_clip", fake_process)
    monkeypatch.setattr(render_pipeline, "lookup_cached", lambda *_: None)
    monkeypatch.setattr(
        render_pipeline,
        "record_cached",
        lambda key, files, clips_metadata=None: {"files": files},
    )
    mixed: dict = {}

    def fake_concat(parts, output_path):
        mixed["parts"] = list(parts)
        mixed["out"] = output_path
        Path(output_path).write_bytes(b"mix")
        return output_path

    monkeypatch.setattr(render_pipeline, "_concat_parts", fake_concat)

    progress: list = []
    result = render_pipeline.render_clips(
        "https://youtu.be/a",
        CLIPS,
        "id",
        progress=lambda current, total: progress.append((current, total)),
        mix=True,
    )

    assert [source for source, _ in calls] == [
        "https://youtu.be/a",
        "https://youtu.be/b",
    ]
    assert len(mixed["parts"]) == 2
    assert result["files"] == [mixed["out"]]
    assert result["mix"] is True
    assert result["total_variants_generated"] == 1
    assert progress[-1] == (2, 2)
    Path(mixed["out"]).unlink(missing_ok=True)


def test_worker_forwards_mix_flag(monkeypatch):
    seen: dict = {}

    def fake_render(video_url, clips, lang, progress=None, mix=False):
        seen.update(video_url=video_url, mix=mix)
        return {"status": "success", "files": ["output/MIX.mp4"]}

    monkeypatch.setattr("backend.services.render_pipeline.render_clips", fake_render)
    monkeypatch.setattr(
        "backend.core.task_results.set_progress_sync",
        lambda task_id, current, total: None,
    )
    monkeypatch.setattr(
        "backend.core.task_results.record_attempt", lambda task_id, attempt: None
    )

    context = SimpleNamespace(message=SimpleNamespace(task_id="task-1", labels={}))
    result = asyncio.run(
        worker_module.process_all_clips_task.original_func(
            "https://youtu.be/a",
            CLIPS,
            "id",
            mix_sources=True,
            context=context,
        )
    )

    assert seen["mix"] is True
    assert result["status"] == "success"
