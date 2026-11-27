"""Pemisahan TTS / STT / LLM."""

import pytest

from backend.core import transcription
from backend.services import model_discovery, tts


def test_tts_provider_default_auto(monkeypatch):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    assert tts.tts_provider() == "auto"
    monkeypatch.setenv("TTS_PROVIDER", "camb")
    assert tts.tts_provider() == "camb"
    monkeypatch.setenv("TTS_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        tts.tts_provider()


def test_stt_provider_default_auto(monkeypatch):
    monkeypatch.delenv("STT_PROVIDER", raising=False)
    assert transcription.stt_provider() == "auto"
    monkeypatch.setenv("STT_PROVIDER", "openai")
    assert transcription.stt_provider() == "openai"
    monkeypatch.setenv("STT_PROVIDER", "bogus")
    with pytest.raises(ValueError):
        transcription.stt_provider()


def test_registries_are_separate():
    assert set(tts.TTS_PROVIDERS) == {"cartesia", "camb", "gtts"}
    assert set(transcription.STT_PROVIDERS) == {"camb", "openai", "groq"}
    assert "cartesia" in model_discovery.MODEL_CATALOG  # tetap ada, bukan dihapus
    assert model_discovery.PROVIDER_KIND["cartesia"] == "tts"
