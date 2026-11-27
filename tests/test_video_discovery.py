"""Auto-discover video sumber dari topik (YouTube/Exa/Tavily/Firecrawl/Selenium+BS4)."""

import pytest

from backend.services import video_discovery as vd


def test_discover_rejects_empty_topic():
    with pytest.raises(ValueError, match="wajib diisi"):
        vd.discover_videos_for_topic("")


def test_discover_clips_to_max_range(monkeypatch):
    monkeypatch.setattr(
        vd,
        "_search_youtube",
        lambda topic, niche, limit: [
            {
                "url": f"https://youtu.be/v{i}",
                "title": f"Video {i}",
                "duration": 300,
                "source": "youtube",
                "channel": None,
                "thumbnail": None,
            }
            for i in range(12)
        ],
    )
    for fn in (
        "_search_exa",
        "_search_tavily",
        "_search_firecrawl",
        "_search_selenium_bs4",
    ):
        monkeypatch.setattr(vd, fn, lambda topic, niche, limit: [])
    monkeypatch.setattr(
        vd,
        "_ai_select_videos",
        lambda topic, niche, candidates, max_select: candidates[:max_select],
    )
    result = vd.discover_videos_for_topic("topik uji", max_videos=3)
    assert len(result) == 3
    assert all(v["duration"] == 300 for v in result)


def test_discover_filters_short_videos(monkeypatch):
    monkeypatch.setattr(
        vd,
        "_search_youtube",
        lambda topic, niche, limit: [
            {
                "url": "https://youtu.be/short",
                "title": "Pendek",
                "duration": 60,
                "source": "youtube",
                "channel": None,
                "thumbnail": None,
            },
            {
                "url": "https://youtu.be/long",
                "title": "Panjang",
                "duration": 300,
                "source": "youtube",
                "channel": None,
                "thumbnail": None,
            },
        ],
    )
    for fn in (
        "_search_exa",
        "_search_tavily",
        "_search_firecrawl",
        "_search_selenium_bs4",
    ):
        monkeypatch.setattr(vd, fn, lambda topic, niche, limit: [])
    monkeypatch.setattr(
        vd,
        "_ai_select_videos",
        lambda topic, niche, candidates, max_select: candidates[:max_select],
    )
    result = vd.discover_videos_for_topic("topik", min_duration_seconds=240)
    assert [v["title"] for v in result] == ["Panjang"]


def test_discover_uses_ai_select_when_many_candidates(monkeypatch):
    monkeypatch.setattr(
        vd,
        "_search_youtube",
        lambda topic, niche, limit: [
            {
                "url": f"https://youtu.be/v{i}",
                "title": f"Video {i}",
                "duration": 300,
                "source": "youtube",
                "channel": None,
                "thumbnail": None,
            }
            for i in range(12)
        ],
    )
    for fn in (
        "_search_exa",
        "_search_tavily",
        "_search_firecrawl",
        "_search_selenium_bs4",
    ):
        monkeypatch.setattr(vd, fn, lambda topic, niche, limit: [])

    chosen_order: list = []

    def fake_ai_select(topic, niche, candidates, max_select):
        chosen_order.extend([c["url"] for c in candidates])
        # Simulasikan AI memilih indeks 1 dan 0.
        return [candidates[1], candidates[0]][:max_select]

    monkeypatch.setattr(vd, "_ai_select_videos", fake_ai_select)
    result = vd.discover_videos_for_topic("topik uji", max_videos=2)
    assert [v["url"] for v in result] == ["https://youtu.be/v1", "https://youtu.be/v0"]


def test_discover_returns_empty_when_no_sources(monkeypatch):
    for fn in (
        "_search_youtube",
        "_search_exa",
        "_search_tavily",
        "_search_firecrawl",
        "_search_selenium_bs4",
    ):
        monkeypatch.setattr(vd, fn, lambda topic, niche, limit: [])
    assert vd.discover_videos_for_topic("topik") == []
