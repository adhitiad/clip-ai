from backend.services.viral_predictor import (
    _count_power_words,
    _duration_score,
    _score_from_real_performance,
    get_niche_threshold,
    predict_viral_score,
    rule_based_score,
)

FEATURES = [0.8, 2.0, 1.0, 0.5, 1.0, 0.7, 0.4, 0.6, 0.3, 0.9]


def test_rule_based_score_is_bounded():
    assert 1.0 <= rule_based_score(FEATURES) <= 10.0


def test_niche_thresholds():
    assert get_niche_threshold("gaming") == 7.5
    assert get_niche_threshold("unknown-niche") == 6.5


def test_duration_score_prefers_short_form_middle():
    assert _duration_score(50) > _duration_score(5)
    assert _duration_score(0) == 0.0


def test_power_word_counter():
    assert _count_power_words("Rahasia viral yang belum terungkap") == 3


def test_predict_viral_score_contract_and_threshold_override():
    result = predict_viral_score(
        {"title_en": "Rahasia viral", "start_time": 10, "end_time": 55},
        threshold=9.5,
    )
    assert result["ml_threshold_used"] == 9.5
    assert 1.0 <= result["ml_viral_score"] <= 10.0
    assert isinstance(result["ml_should_render"], bool)
    assert isinstance(result["ml_features"], list)
    assert len(result["ml_features"]) == 10
    assert result["ml_confidence"] == "rule_based"


def test_real_performance_score_rewards_engagement():
    assert _score_from_real_performance(0, 0, 0) == 1.0
    assert _score_from_real_performance(100_000, 10_000, 2_000) > (
        _score_from_real_performance(100, 1, 0)
    )
