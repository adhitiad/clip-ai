"""Guard: smoke render memakai transkrip asli, bukan kata statis."""

from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "smoke_render.py"


def test_smoke_render_uses_real_transcription():
    text = SOURCE.read_text(encoding="utf-8")
    assert "transcribe_words" in text
    assert "SMOKE" not in text
    assert "stub" not in text.lower()
