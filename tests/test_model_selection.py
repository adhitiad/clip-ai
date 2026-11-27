from pathlib import Path

from backend.services.model_discovery import (
    FREE_MODELS,
    MODEL_CATALOG,
    PROVIDER_MODEL_PROVIDER,
    _is_free,
    _sort_free_first,
    free_model_count,
    list_available_models,
    save_model_choice,
    select_provider_model,
)


def test_nvidia_nim_registered():
    assert PROVIDER_MODEL_PROVIDER["nvidia"] == "nvidia"
    assert MODEL_CATALOG["nvidia"]
    assert free_model_count("nvidia") > 0
    assert "meta/llama-3.1-8b-instruct" in MODEL_CATALOG["nvidia"]


def test_free_models_sorted_first():
    ordered = _sort_free_first("openai", ["gpt-5.2", "gpt-4o-mini", "gpt-4o"])
    assert ordered[0] == "gpt-4o-mini"
    assert _is_free("openrouter", "meta/llama-3.1-8b-instruct:free")
    assert _is_free("nvidia", "meta/llama-3.2-1b-instruct")
    assert FREE_MODELS["ollama"]


def test_catalog_available_without_keys(monkeypatch):
    for key in ("OPENAI_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY", "OLLAMA_HOST"):
        monkeypatch.delenv(key, raising=False)
    found = list_available_models("openai")
    assert "openai" in found
    assert found["openai"]


def test_select_manual_when_nothing_found(monkeypatch):
    monkeypatch.setattr(
        "backend.services.model_discovery.list_available_models", lambda **_: {}
    )
    answers = iter(["openai/gpt-4o-mini"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert select_provider_model() == ("openai", "gpt-4o-mini")


def test_select_by_number(monkeypatch, capsys):
    monkeypatch.setattr(
        "backend.services.model_discovery.list_available_models",
        lambda **_: {"openai": ["gpt-4o-mini"]},
    )
    answers = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert select_provider_model() == ("openai", "gpt-4o-mini")
    assert "gpt-4o-mini" in capsys.readouterr().out


def test_save_model_choice_strips_bom(tmp_path: Path):
    env = tmp_path / ".env"
    save_model_choice("\ufeffopenai", "gpt-4o-mini", env)
    assert "AGENT_PROVIDER=openai" in env.read_text()


def test_save_model_choice_preserves_other_env(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("SECRET_KEY=abc\nAGENT_PROVIDER=groq\nAGENT_MODEL=lama\nPORT=8000\n")
    save_model_choice("openai", "gpt-4o-mini", env)
    content = env.read_text()
    assert "AGENT_PROVIDER=openai" in content
    assert "AGENT_MODEL=gpt-4o-mini" in content
    assert "SECRET_KEY=abc" in content
    assert "PORT=8000" in content
