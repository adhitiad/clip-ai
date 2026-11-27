"""Guard: TTS terpisah di backend.services.tts (Cartesia -> Camb -> gTTS)."""

from backend.services import tts


class FakeResp:
    def __init__(self, content=b"ID3audio", chunks=None):
        self.content = content
        self._chunks = chunks or [b"audio"]

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        return self._chunks


def test_cartesia_request_shape(monkeypatch, tmp_path):
    import os

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResp()

    monkeypatch.setattr(tts.requests, "post", fake_post)
    monkeypatch.setenv("CARTESIA_API_KEY", "sk_car_test")
    monkeypatch.setenv("CARTESIA_VOICE_ID", "voice-123")
    output = str(tmp_path / "tts.mp3")

    result = tts.tts_cartesia("halo", "id", output)
    assert captured["url"] == tts.CARTESIA_TTS_URL
    assert captured["headers"]["Cartesia-Version"] == tts.CARTESIA_VERSION
    assert captured["json"]["voice"] == {"id": "voice-123"}
    assert result == output
    assert os.path.getsize(output) > 0  # file MP3 nyata


def test_camb_request_shape(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResp(chunks=[b"a", b"b"])

    monkeypatch.setattr(tts.requests, "post", fake_post)
    monkeypatch.setenv("CAMB_API_KEY", "camb-test")
    output = str(tmp_path / "tts.mp3")

    result = tts.tts_camb("halo", "id", output)
    assert captured["url"] == tts.CAMB_TTS_URL
    assert captured["headers"]["x-api-key"] == "camb-test"
    assert captured["json"]["language"] == "id-id"
    assert result == output


def test_generate_tts_respects_selected_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_PROVIDER", "camb")
    calls = []
    monkeypatch.setattr(tts, "tts_cartesia", lambda *a, **k: calls.append("cartesia"))
    monkeypatch.setattr(
        tts, "tts_camb", lambda *a, **k: calls.append("camb") or "out.mp3"
    )
    assert tts.generate_tts("halo")
    assert calls == ["camb"]


def test_voice_providers_are_categorized_not_removed():
    from backend.services.model_discovery import MODEL_CATALOG, PROVIDER_KIND

    assert "cartesia" in MODEL_CATALOG
    assert "camb" in MODEL_CATALOG
    assert PROVIDER_KIND["cartesia"] == "tts"
    assert PROVIDER_KIND["camb"] == "tts"
    assert PROVIDER_KIND["nvidia"] == "llm"
