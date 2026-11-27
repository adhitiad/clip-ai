"""Guard: transkripsi Camb dipakai walau OPENAI/GROQ kosong."""

import backend.core.transcription as tr


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_camb_is_first_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("CAMB_API_KEY", "test-key")
    monkeypatch.setattr(
        tr,
        "_camb_transcribe",
        lambda path, key, language="": [
            {"start": 0.0, "end": 1.0, "text": "Halo dunia"}
        ],
    )
    assert tr.transcribe("dummy.mp3") == "Halo dunia"
    assert tr.transcribe_words("dummy.mp3") == [
        {"text": "Halo", "start": 0.0, "end": 0.5},
        {"text": "dunia", "start": 0.5, "end": 1.0},
    ]


def test_camb_create_poll_result(monkeypatch, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setenv("CAMB_API_KEY", "test-key")
    monkeypatch.setenv("CAMB_STT_LANGUAGE", "en-us")
    monkeypatch.setattr(tr.time, "sleep", lambda _: None)

    def fake_post(url, **kwargs):
        assert url.endswith("/transcribe")
        assert kwargs["data"]["language"] == "en-us"
        return _Resp({"task_id": "task-1"})

    def fake_get(url, **kwargs):
        if url.endswith("/transcribe/task-1"):
            return _Resp({"status": "SUCCESS", "run_id": 42})
        if url.endswith("/transcription-result/42"):
            return _Resp(
                {
                    "transcript": [
                        {"start": 0.0, "end": 1.0, "text": "Halo", "speaker": "S0"}
                    ]
                }
            )
        raise AssertionError(url)

    monkeypatch.setattr(tr.requests, "post", fake_post)
    monkeypatch.setattr(tr.requests, "get", fake_get)

    result = tr._camb_transcribe(str(audio), "test-key")
    assert result == [{"start": 0.0, "end": 1.0, "text": "Halo"}]
