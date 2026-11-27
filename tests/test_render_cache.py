"""Render cache: hash input, manifest artefak, dan cache hit di worker."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.services import render_cache
from workers import worker as worker_module

CLIPS = [{"title_en": "Edit Cepat", "start_time": 0, "end_time": 15}]


def test_job_key_deterministic_and_sensitive(monkeypatch):
    monkeypatch.setenv("AGENT_PROVIDER", "nvidia")
    key = render_cache.compute_job_key("https://youtu.be/a", CLIPS, "id")
    assert key == render_cache.compute_job_key("https://youtu.be/a", CLIPS, "id")
    assert render_cache.compute_job_key("https://youtu.be/b", CLIPS, "id") != key
    assert render_cache.compute_job_key("https://youtu.be/a", CLIPS, "en") != key

    monkeypatch.setenv("AGENT_PROVIDER", "openai")
    assert render_cache.compute_job_key("https://youtu.be/a", CLIPS, "id") != key


def test_manifest_roundtrip_and_invalid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        render_cache,
        "probe_file",
        lambda path: {
            "path": path,
            "duration": 6.1,
            "size_kb": 1140.2,
            "video_codec": "h264",
            "width": 720,
            "height": 1280,
        },
    )
    output = tmp_path / "FINAL_Edit_Cepat.mp4"
    output.write_bytes(b"x" * 1024)

    entry = render_cache.record_cached("abc", [str(output)], output_dir=str(tmp_path))
    assert entry["artifacts"][0]["duration"] == 6.1
    assert render_cache.lookup_cached("abc", output_dir=str(tmp_path)) == entry
    assert render_cache.lookup_cached("missing", output_dir=str(tmp_path)) is None

    saved = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert "abc" in saved

    output.unlink()
    assert render_cache.lookup_cached("abc", output_dir=str(tmp_path)) is None


def test_worker_skips_render_on_cache_hit(monkeypatch):
    entry = {"files": ["output/FINAL_Edit_Cepat.mp4"]}
    monkeypatch.setattr(
        "backend.services.render_pipeline.lookup_cached",
        lambda key, output_dir="output": entry,
    )
    monkeypatch.setattr(
        "backend.services.render_pipeline.record_cached",
        lambda *args, **kwargs: pytest.fail("cache hit tidak boleh menulis manifest"),
    )
    monkeypatch.setattr(
        "backend.services.video_engine.process_clip",
        lambda *args, **kwargs: pytest.fail("cache hit tidak boleh render"),
    )
    monkeypatch.setattr(
        "backend.core.task_results.set_progress_sync",
        lambda task_id, current, total: None,
    )
    monkeypatch.setattr(
        "backend.core.task_results.record_attempt",
        lambda task_id, attempt: None,
    )

    context = SimpleNamespace(message=SimpleNamespace(task_id="task-1", labels={}))
    result = asyncio.run(
        worker_module.process_all_clips_task.original_func(
            "https://youtu.be/a", CLIPS, "id", context=context
        )
    )

    assert result["cached"] is True
    assert result["files"] == entry["files"]
    assert result["total_variants_generated"] == 1
