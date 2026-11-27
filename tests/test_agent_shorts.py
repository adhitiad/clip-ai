import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.core.agent import build_shorts_prompt, plan_shorts
from backend.core.auth import get_current_active_user, get_db
from backend.core.models import ShortsClipPlan, ShortsPlan
from backend.main import app
from backend.routes.agent import (
    ShortsRequest,
    _apply_plan_to_clips,
    _build_clips_sync,
    _request_sources,
    _select_mixed_clips,
)
from backend.services.model_discovery import resolve_provider_model


def _plan() -> ShortsPlan:
    return ShortsPlan(
        platform="shorts",
        topic="tips editing video",
        clips=(
            ShortsClipPlan(
                start_time=5,
                end_time=20,
                hook="Jangan skip ini!",
                title="Edit Cepat",
                caption="Potong di beat",
                hashtags=("#shorts", "#editing"),
            ),
        ),
    )


def test_build_shorts_prompt_contains_quality_rules():
    prompt = build_shorts_prompt("tips editing", "tiktok", "contoh", 2, "id")
    assert "tiktok" in prompt
    assert "tips editing" in prompt
    assert "1,5 detik" in prompt
    assert "JSON" in prompt


def test_apply_plan_to_clips_merges_copy_and_timing():
    clips = [{"start_time": 5, "end_time": 20, "title_id": "lama"}]
    result = _apply_plan_to_clips(clips, _plan(), "id")
    assert result[0]["start_time"] == 5
    assert result[0]["title_id"] == "Edit Cepat"
    assert "#shorts" in result[0]["desc_id"]


def test_plan_shorts_structured_output(monkeypatch):
    expected = _plan()

    class FakeStructured:
        def invoke(self, _prompt):
            return expected

    class FakeLLM:
        def with_structured_output(self, _schema):
            return FakeStructured()

    monkeypatch.setattr("backend.core.agent.agent_llm", lambda **_: FakeLLM())
    result = plan_shorts("tips editing", platform="reels", max_clips=1)
    assert result == expected


def test_plan_shorts_truncates_to_max_clips(monkeypatch):
    from backend.core import agent as agent_core

    many = agent_core.ShortsPlan(
        platform="shorts",
        topic="tips editing",
        clips=[
            agent_core.ShortsClipPlan(
                start_time=index * 5,
                end_time=index * 5 + 10,
                hook=f"Hook {index}",
                title=f"Judul {index}",
                caption="Caption",
            )
            for index in range(4)
        ],
    )

    class FakeStructured:
        def invoke(self, _prompt):
            return many

    class FakeLLM:
        def with_structured_output(self, _schema):
            return FakeStructured()

    monkeypatch.setattr("backend.core.agent.agent_llm", lambda **_: FakeLLM())
    assert len(plan_shorts("tips editing", max_clips=2).clips) == 2


def test_resolve_provider_model_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_PROVIDER", "groq")
    monkeypatch.setenv("AGENT_MODEL", "gpt-oss-120b")
    assert resolve_provider_model(None, None) == ("groq", "gpt-oss-120b")


def test_uuid7_generation():
    generated = uuid.uuid7()
    assert generated.version == 7


def test_agent_shorts_route_requires_video_url_for_render():
    app.dependency_overrides[get_current_active_user] = lambda: type(
        "U", (), {"id": 1}
    )()
    app.dependency_overrides[get_db] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.post(
                "/agent/shorts",
                json={
                    "topic": "tips editing",
                    "render_video": True,
                    "auto_discover": False,
                },
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_agent_shorts_brief_without_render(monkeypatch):
    app.dependency_overrides[get_current_active_user] = lambda: type(
        "U", (), {"id": 1}
    )()
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr("backend.core.agent.plan_shorts", lambda **_: _plan())
    monkeypatch.setattr("backend.routes.agent.plan_shorts", lambda **_: _plan())
    try:
        with TestClient(app) as client:
            response = client.post("/agent/shorts", json={"topic": "tips editing"})
        assert response.status_code == 200
        assert response.json()["status"] == "brief"
        assert response.json()["brief"]["clips"][0]["title"] == "Edit Cepat"
    finally:
        app.dependency_overrides.clear()


def _mix_request(urls: list[str], **kwargs) -> ShortsRequest:
    return ShortsRequest(
        topic="gol drama detik terakhir",
        video_urls=urls,
        render_video=True,
        **kwargs,
    )


def test_request_sources_merges_and_dedupes():
    request = ShortsRequest(
        topic="gol",
        video_url=" https://youtu.be/a ",
        video_urls=["https://youtu.be/a", "https://youtu.be/b"],
    )
    assert _request_sources(request) == ["https://youtu.be/a", "https://youtu.be/b"]


def test_select_mixed_clips_round_robin():
    groups = [
        [{"viral_score": 90}],
        [{"viral_score": 80}, {"viral_score": 10}],
    ]
    assert [c["viral_score"] for c in _select_mixed_clips(groups, 3)] == [
        90,
        80,
        10,
    ]


def test_build_clips_sync_tags_source(monkeypatch):
    monkeypatch.setattr(
        "backend.utils.youtube.get_video_info",
        lambda url: {"duration": 300, "title": "judul " + url[-1]},
    )
    monkeypatch.setattr(
        "backend.utils.youtube.check_and_get_youtube_subs", lambda *_: "transkrip"
    )
    batches = iter(
        [
            [{"start_time": 0, "end_time": 10, "viral_score": 90}],
            [{"start_time": 5, "end_time": 15, "viral_score": 80}],
        ]
    )
    monkeypatch.setattr(
        "backend.core.ai_pipeline.process_video_ai_logic", lambda **_: next(batches)
    )

    clips = _build_clips_sync(
        _mix_request(["https://youtu.be/a", "https://youtu.be/b"], max_clips=2)
    )
    assert [clip["source_url"] for clip in clips] == [
        "https://youtu.be/a",
        "https://youtu.be/b",
    ]
    assert all(clip["source_title"] for clip in clips)


def test_build_clips_sync_rejects_short_source_in_mix(monkeypatch):
    durations = {"a": 100, "b": 300}
    monkeypatch.setattr(
        "backend.utils.youtube.get_video_info",
        lambda url: {"duration": durations[url[-1]], "title": ""},
    )
    monkeypatch.setattr(
        "backend.utils.youtube.check_and_get_youtube_subs", lambda *_: "transkrip"
    )
    monkeypatch.setattr(
        "backend.core.ai_pipeline.process_video_ai_logic",
        lambda **_: [{"start_time": 0, "end_time": 10, "viral_score": 50}],
    )

    with pytest.raises(HTTPException) as exc:
        _build_clips_sync(
            _mix_request(["https://youtu.be/a", "https://youtu.be/b"], max_clips=2)
        )
    assert exc.value.status_code == 422
    assert "Minimal 2 video sumber" in exc.value.detail
    assert "Sumber terlalu pendek" in exc.value.detail


def test_agent_shorts_render_multi_source_queues_mix(monkeypatch):
    from types import SimpleNamespace

    app.dependency_overrides[get_current_active_user] = lambda: type(
        "U", (), {"id": 1}
    )()
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr("backend.routes.agent.check_rate_limit", lambda _key: None)
    monkeypatch.setattr("backend.routes.agent.plan_shorts", lambda **_: _plan())
    monkeypatch.setattr(
        "backend.routes.agent._build_clips_sync",
        lambda request: [
            {"start_time": 0, "end_time": 10, "source_url": url}
            for url in request.video_urls
        ],
    )
    monkeypatch.setattr("backend.routes.agent.get_request_id", lambda: "req-1")
    monkeypatch.setattr("backend.routes.agent.current_traceparent", lambda: None)
    queued: dict = {}

    async def fake_kiq(*args, **kwargs):
        queued["args"] = args
        queued["kwargs"] = kwargs
        return SimpleNamespace(task_id="task-1")

    monkeypatch.setattr(
        "workers.worker.process_all_clips_task", SimpleNamespace(kiq=fake_kiq)
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/agent/shorts",
                json={
                    "topic": "tips editing",
                    "render_video": True,
                    "video_urls": ["https://youtu.be/a", "https://youtu.be/b"],
                    "max_clips": 2,
                },
            )
        assert response.status_code == 200
        assert response.json()["mix_sources"] is True
        assert response.json()["sources"] == [
            "https://youtu.be/a",
            "https://youtu.be/b",
        ]
        assert queued["kwargs"]["mix_sources"] is True
    finally:
        app.dependency_overrides.clear()
