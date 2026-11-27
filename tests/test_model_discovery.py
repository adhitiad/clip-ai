import importlib.util

import pytest

from backend.services.model_discovery import (
    MODEL_CATALOG,
    build_model_string,
    default_provider_model,
    discover_models,
)


def test_catalog_covers_common_providers():
    for provider in [
        "openai",
        "anthropic",
        "gemini",
        "groq",
        "deepseek",
        "grok",
        "mistral",
        "ollama",
        "openrouter",
        "cloudflare",
        "cartesia",
        "camb",
        "meta/muse",
        "glm",
        "minmax",
        "kimi",
    ]:
        assert provider in MODEL_CATALOG
        assert MODEL_CATALOG[provider]


def test_build_model_string():
    assert build_model_string("openai", "gpt-5.2") == "openai/gpt-5.2"


def test_discover_models_matches_installed_packages():
    from backend.services.model_discovery import _sort_free_first

    found = discover_models()
    for provider in found:
        assert importlib.util.find_spec(f"langchain_{provider}") is not None
        assert found[provider] == _sort_free_first(provider, MODEL_CATALOG[provider])


def test_default_provider_model_consistent_with_discover():
    provider, model = default_provider_model()
    if provider:
        assert provider in MODEL_CATALOG
        assert model is not None


def test_agent_llm_noninteractive_returns_model(monkeypatch):
    if not importlib.util.find_spec("langchain_groq"):
        pytest.skip("langchain_groq tidak terpasang di environment ini")
    monkeypatch.setenv("AGENT_PROVIDER", "groq")
    monkeypatch.setenv("AGENT_MODEL", "llama-3.1-8b-instant")
    from backend.core.agent import agent_llm

    assert agent_llm(interactive=False) is not None
