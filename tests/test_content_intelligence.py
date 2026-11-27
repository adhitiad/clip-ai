"""Content intelligence: sanitasi tren, merge brief, dan skor viral."""

from backend.services import content_intelligence as ci


def test_sanitize_terms():
    assert ci.sanitize_terms(["  trend\x00A  ", "", "B" * 100]) == [
        "trendA",
        "B" * 80,
    ]
    assert ci.sanitize_terms("bukan list") == []


def test_apply_brief_to_clips_merges_copy_and_trends():
    clips = [{"start_time": 0, "end_time": 15}]
    brief = {
        "clips": [
            {
                "title": "Edit Cepat",
                "hook": "Jangan skip!",
                "caption": "Potong di beat",
                "hashtags": ["#shorts"],
            }
        ]
    }
    result = ci.apply_brief_to_clips(clips, brief, "id", ["trend A"])
    assert result[0]["title_id"] == "Edit Cepat"
    assert result[0]["desc_id"] == "Jangan skip! Potong di beat #shorts trend A"
    assert result[0]["agent_hashtags"] == ["#shorts"]
    assert result[0]["target_language"] == "id"


def test_score_clips_attaches_viral_result(monkeypatch):
    monkeypatch.setattr(
        "backend.services.viral_predictor.predict_viral_score",
        lambda clip_metadata, threshold=None: {
            **clip_metadata,
            "ml_viral_score": 8.0,
            "ml_should_render": True,
        },
    )
    result = ci.score_clips([{"title_id": "A"}])
    assert result[0]["ml_viral_score"] == 8.0
    assert result[0]["ml_should_render"] is True
