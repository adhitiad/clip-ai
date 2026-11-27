"""Model internal @dataclass + numpy/pandas."""

from backend.core.models import (
    ClipStat,
    ProviderInfo,
    ShortsClipPlan,
    ShortsPlan,
    ViralFeatures,
)
from backend.services.viral_predictor import batch_predict_and_filter, rule_based_score


def test_viral_features_dataclass_vector():
    features = ViralFeatures.from_list([1.0] * 10)
    assert features.as_array().shape == (10,)
    assert 1.0 <= rule_based_score(features) <= 10.0


def test_shorts_plan_dataclass_roundtrip():
    plan = ShortsPlan(
        platform="reels",
        topic="bola",
        clips=(ShortsClipPlan(0, 30, "hook", "judul", "caption", ("#bola",)),),
    )
    data = plan.as_dict()
    assert isinstance(data["clips"], list)
    assert data["clips"][0]["hashtags"] == ["#bola"]


def test_provider_info_dataclass():
    provider = ProviderInfo("nvidia", "NIM", "🎬", "llm", free=True, models=("m",))
    assert provider.icon == "🎬"
    assert provider.free


def test_batch_filter_uses_pandas():
    clips = [
        {"title_en": f"klip {i}", "start_time": 0, "end_time": 45} for i in range(3)
    ]
    result = batch_predict_and_filter(clips, threshold=1.0)
    assert len(result) == 3
    scores = [item["ml_viral_score"] for item in result]
    assert scores == sorted(scores, reverse=True)


def test_clip_stat_day_key():
    stat = ClipStat(1, "judul", 8)
    assert len(stat.day_key()) == 10
