"""T-11: validasi input & path."""

from pathlib import Path

import pytest

from backend.core.validation import (
    is_within_root,
    resolve_confined_path,
    sanitize_filename,
    validate_lang,
    validate_search_type,
    validate_text,
)


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename("Judul Viral! #1") == "Judul_Viral_1"
    assert sanitize_filename("   ") == "clip"
    assert "\ufeff" not in sanitize_filename("\ufeffHalo")


def test_path_confinement(tmp_path: Path):
    allowed = tmp_path / "temp"
    allowed.mkdir()
    inside = allowed / "video.mp4"
    inside.write_bytes(b"x")

    assert is_within_root(inside, allowed)
    assert resolve_confined_path(str(inside), allowed) == inside.resolve()
    with pytest.raises(ValueError):
        resolve_confined_path(str(tmp_path / "luar.mp4"), allowed)


def test_lang_and_search_type():
    assert validate_lang("ID") == "id"
    with pytest.raises(ValueError):
        validate_lang("fr")
    assert validate_search_type("DEEP-LITE") == "deep-lite"
    with pytest.raises(ValueError):
        validate_search_type("bogus")


def test_validate_text():
    assert validate_text("  halo  ", "judul", 10) == "halo"
    with pytest.raises(ValueError):
        validate_text("", "judul", 10)
    with pytest.raises(ValueError):
        validate_text("a" * 11, "judul", 10)
