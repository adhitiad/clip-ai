from backend.utils.captioning import format_timestamp


def test_format_timestamp_includes_milliseconds():
    assert format_timestamp(3661.5) == "01:01:01,500"
    assert format_timestamp(0) == "00:00:00,000"
