"""LLM (chat) discovery via LangChain — HANYA untuk AI teks.

TTS ada di backend/services/tts.py, STT di backend/core/transcription.py.
Jangan daftarkan provider suara di sini.
"""

import importlib.util
import os
from pathlib import Path
from typing import Any, Optional

from backend.core.env import load_env
from backend.services import provider_health

load_env("backend")

ROOT_DIR = Path(__file__).resolve().parents[2]

# Env key per provider untuk pencarian model live.
_PROVIDER_KEY_ENV: dict[str, str] = {
    "cartesia": "CARTESIA_API_KEY",
    "camb": "CAMB_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "grok": "XAI_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRALAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openroute": "OPENROUTER_API_KEY",
    "cloudflare": "CLOUDFLARE_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "minmax": "MINIMAX_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "meta/muse": "META_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    "huggingface": "HUGGINGFACEHUB_API_TOKEN",
    "nvidia": "NVIDIA_API_KEY",
}

# Endpoint daftar model. ``None`` pada header berarti key dipakai sebagai query.
_LIVE_ENDPOINTS: dict[str, tuple[str, str, str]] = {
    "openai": ("https://api.openai.com/v1/models", "data", "id"),
    "groq": ("https://api.groq.com/openai/v1/models", "data", "id"),
    "openrouter": ("https://openrouter.ai/api/v1/models", "data", "id"),
    "openroute": ("https://openrouter.ai/api/v1/models", "data", "id"),
    "deepseek": ("https://api.deepseek.com/models", "data", "id"),
    "mistral": ("https://api.mistral.ai/v1/models", "data", "id"),
    "grok": ("https://api.x.ai/v1/models", "data", "id"),
    "xai": ("https://api.x.ai/v1/models", "data", "id"),
    "anthropic": ("https://api.anthropic.com/v1/models", "data", "id"),
    "nvidia": ("https://integrate.api.nvidia.com/v1/models", "data", "id"),
}

# Pemetaan kunci katalog -> nama ``model_provider`` yang diterima LangChain
# (init_chat_model). Provider yang belum ada langsung di LangChain diarahkan
# melalui "litellm" (bisa menunjuk ke OpenRouter/dll).
PROVIDER_MODEL_PROVIDER: dict[str, str] = {
    "cartesia": "litellm",
    "camb": "litellm",
    "openai": "openai",
    "gemini": "google_genai",
    "anthropic": "anthropic",
    "openroute": "openrouter",
    "openrouter": "openrouter",
    "cloudflare": "litellm",
    "grok": "xai",
    "groq": "groq",
    "meta/muse": "meta",
    "glm": "litellm",
    "minmax": "litellm",
    "kimi": "litellm",
    "deepseek": "deepseek",
    "mistral": "mistralai",
    "ollama": "ollama",
    "huggingface": "huggingface",
    "nvidia": "nvidia",
}

# Kategori tiap provider: llm | tts | stt.
# TTS dan STT tetap terdaftar di katalog, tapi tidak dipakai sebagai chat model.
PROVIDER_KIND: dict[str, str] = {
    "cartesia": "tts",
    "camb": "tts",
}
for _name in (
    "openai",
    "gemini",
    "anthropic",
    "openroute",
    "openrouter",
    "cloudflare",
    "grok",
    "groq",
    "meta/muse",
    "glm",
    "minmax",
    "kimi",
    "deepseek",
    "mistral",
    "ollama",
    "huggingface",
    "nvidia",
):
    PROVIDER_KIND[_name] = "llm"


# Model default per provider (referensi saat belum ada paket terpasang).
MODEL_CATALOG: dict[str, list[str]] = {
    "cartesia": ["sonic-2"],
    "camb": ["mars-8.1-flash-beta"],
    "openai": [
        "gpt-5.2",
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4o-mini",
        "gpt-4o",
        "o3",
    ],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "anthropic": [
        "claude-opus-4-1",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-3-7-sonnet-latest",
    ],
    "openroute": [
        "openai/gpt-5.2",
        "anthropic/claude-opus-4-1",
        "deepseek/deepseek-chat",
    ],
    "openrouter": [
        "openai/gpt-5.2",
        "anthropic/claude-opus-4-1",
        "deepseek/deepseek-chat",
    ],
    "cloudflare": ["@cf/meta/llama-3.3-70b-instruct"],
    "grok": ["grok-4", "grok-3", "grok-code-fast-1"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gpt-oss-120b"],
    "meta/muse": ["meta-llama/Llama-3.3-70B-Instruct"],
    "glm": ["glm-4", "glm-3-turbo"],
    "minmax": ["minimax-01", "minimax-text-01"],
    "kimi": ["kimi-k2-instruct", "moonshot-v1-8k"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "mistral": ["mistral-large-latest", "mistral-medium-latest"],
    "ollama": ["llama3.3", "gpt-oss:20b", "qwen3:8b"],
    "huggingface": ["meta-llama/Llama-3.1-8B-Instruct"],
    # NVIDIA NIM (build.nvidia.com) — gratis dengan nvapi key, diurutkan gratis dulu.
    "nvidia": [
        "nvidia/nemotron-3.5-super-vl-120b-a12b",  # default (masih aktif di NIM)
        "google/gemma-3-4b-it",
        "z-ai/glm-5.3-flash",
        "meta/llama-3.2-1b-instruct",
        "meta/llama-3.2-3b-instruct",
        "meta/llama-3.1-8b-instruct",
        "google/gemma-7b",
        "google/codegemma-7b",
        "microsoft/phi-4-mini-instruct",
        "nvidia/nvidia-nemotron-nano-9b-v2",
        "qwen/qwen2.5-coder-32b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-v4-flash",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "moonshotai/kimi-k2-instruct",
        "minimaxai/minimax-m2.5",
        "z-ai/glm4.7",
        "mistralai/mixtral-8x7b-instruct",
        "upstage/solar-10.7b-instruct",
    ],
}

# Model yang diketahui GRATIS / berkuota gratis (dahulukan dalam daftar & select).
# Sumber: tier gratis build.nvidia.com (NIM), Gemini flash, Groq, OpenRouter :free,
# Ollama lokal (tanpa biaya), dan model kecil gratis lainnya.
FREE_MODELS: dict[str, set[str]] = {
    "cartesia": set(),
    "camb": set(),
    "nvidia": set(
        MODEL_CATALOG["nvidia"][:13]
    ),  # semua NIM di atas gratis/berkuota gratis
    "groq": {"llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gpt-oss-120b"},
    "gemini": {"gemini-2.5-flash", "gemini-2.0-flash"},
    "openrouter": set(),  # diisi dari suffix ":free" saat pencarian live
    "openroute": set(),
    "deepseek": {"deepseek-chat", "deepseek-reasoner"},
    "ollama": set(MODEL_CATALOG["ollama"]),  # lokal gratis
    "huggingface": set(MODEL_CATALOG["huggingface"]),
    "cloudflare": set(MODEL_CATALOG["cloudflare"]),
    "mistral": {"mistral-small-latest"},
    "grok": set(),
    "openai": {"gpt-4o-mini"},
    "anthropic": set(),
    "glm": {"glm-3-turbo"},
    "minmax": set(),
    "kimi": {"moonshot-v1-8k"},
    "meta/muse": set(),
    "xai": set(),
}

# Sinyal katalog: latency kasar & tier biaya. Dipakai UI sebagai badge;
# health asli berasal dari provider_health (circuit breaker in-memory).
PROVIDER_HINTS: dict[str, tuple[str, str]] = {
    "nvidia": ("cepat", "free"),
    "groq": ("cepat", "free"),
    "ollama": ("lokal", "free"),
    "gemini": ("cepat", "mixed"),
    "deepseek": ("sedang", "free"),
    "openai": ("sedang", "paid"),
    "anthropic": ("sedang", "paid"),
    "mistral": ("sedang", "paid"),
    "grok": ("sedang", "paid"),
    "openrouter": ("sedang", "mixed"),
    "openroute": ("sedang", "mixed"),
    "cloudflare": ("cepat", "free"),
    "huggingface": ("sedang", "free"),
    "cartesia": ("cepat", "paid"),
    "camb": ("cepat", "paid"),
}


def provider_metadata(provider: str) -> dict:
    latency, cost = PROVIDER_HINTS.get(provider, ("", "unknown"))
    if cost == "unknown":
        cost = (
            "free"
            if _is_free(provider, (MODEL_CATALOG.get(provider) or [""])[0])
            else "paid"
        )
    return {
        "latency_hint": latency,
        "cost_tier": cost,
        "healthy": provider_health.is_healthy(provider),
    }


def _is_free(provider: str, model: str) -> bool:
    lowered = model.lower()
    # Semua NIM di build.nvidia.com gratis/berkuota gratis dengan kunci nvapi-.
    if provider in {"nvidia", "nvidia-nim"}:
        return True
    return (
        model in FREE_MODELS.get(provider, set())
        or lowered.endswith(":free")
        or ":free" in lowered
        or "-free" in lowered
    )


def _sort_free_first(provider: str, models: list[str]) -> list[str]:
    """Gratis lebih dulu, lalu stabil untuk sisanya."""
    return sorted(dict.fromkeys(models), key=lambda m: (not _is_free(provider, m), m))


def free_model_count(provider: str) -> int:
    """Jumlah model gratis untuk provider (dipakai urutan rekomendasi)."""
    return len(FREE_MODELS.get(provider, set()))


def discover_models() -> dict[str, list[str]]:
    """Return {provider: known_models} untuk paket ``langchain_*`` terpasang."""
    found = {}
    for provider in MODEL_CATALOG:
        # LangChain mengasumsikan nama paket langchain_<provider>.
        if importlib.util.find_spec(f"langchain_{provider}"):
            found[provider] = _sort_free_first(provider, MODEL_CATALOG[provider])
    return found


def build_model_string(provider: str, model: str) -> str:
    return f"{provider}/{model}"


def _manual_model() -> str:
    while True:
        value = (
            input("Input provider/model (contoh: openai/gpt-5.2): ")
            .strip()
            .lstrip("\ufeff")
        )
        if value and "/" in value:
            return value
        print("Format harus 'provider/model'.")


def _model_provider(provider: str) -> str:
    return PROVIDER_MODEL_PROVIDER.get(provider, provider)


def resolve_provider_model(provider: str | None, model: str | None) -> tuple[str, str]:
    """Resolve pilihan provider/model: argumen → env (AGENT_*) → katalog default."""
    import os

    resolved_provider = (provider or os.getenv("AGENT_PROVIDER", "")).strip()
    resolved_model = (model or os.getenv("AGENT_MODEL", "")).strip()
    if resolved_provider and resolved_model:
        return resolved_provider, resolved_model
    found = discover_models()
    if resolved_provider:
        default_model = (MODEL_CATALOG.get(resolved_provider) or [""])[0]
        return resolved_provider, resolved_model or default_model
    healthy = {
        name: models
        for name, models in found.items()
        if provider_health.is_healthy(name)
    }
    if healthy:
        found = healthy
    if found:
        chosen = next(iter(found))
        return chosen, (MODEL_CATALOG.get(chosen) or [""])[0]
    raise RuntimeError(
        "Model agent belum dipilih. Set AGENT_PROVIDER/AGENT_MODEL di .env "
        "atau panggil select_chat_model(interactive=True)."
    )


def select_chat_model(
    interactive: bool = True,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> Any:
    """
    Kembalikan LangChain chat model melalui discovery atau input manual.

    - ``provider``/``model`` eksplisit (atau env AGENT_*) dipakai langsung.
    - Interaktif: tampilkan daftar provider terpasang, pilih nomor, fallback
      input manual.
    - Non-interaktif: pakai resolve_provider_model() (provider pertama yang
      terdeteksi bila tidak ada env).
    """

    def _init_model(provider: str, model: str) -> Any:
        from langchain.chat_models import init_chat_model

        kwargs = {"model_provider": _model_provider(provider)}
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            if (
                kwargs["model_provider"] == "openrouter"
                and importlib.util.find_spec("langchain_openrouter") is None
            ):
                # OpenRouter kompatibel OpenAI; pakai ChatOpenAI bila paket
                # langchain-openrouter belum terpasang. Tetap satu jalur LLM.
                from langchain_openai import ChatOpenAI

                fallback: dict[str, Any] = {
                    "model": model,
                    "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                    "base_url": os.getenv(
                        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
                    ),
                }
                if temperature is not None:
                    fallback["temperature"] = temperature
                result = ChatOpenAI(**fallback)
            else:
                result = init_chat_model(model, **kwargs)
        except Exception as exc:
            provider_health.record_failure(provider)
            from backend.core.audit import log_ai_call

            log_ai_call("llm", provider, model, success=False, error=str(exc)[:200])
            raise
        provider_health.record_success(provider)
        from backend.core.audit import log_ai_call

        log_ai_call("llm", provider, model)
        return result

    if provider or model or not interactive:
        chosen_provider, chosen_model = resolve_provider_model(provider, model)
        return _init_model(chosen_provider, chosen_model)

    # Interaktif: cari model tersedia (live + katalog), pilih nomor, atau input manual.
    chosen_provider, chosen_model = select_provider_model()
    save_model_choice(chosen_provider, chosen_model)
    print(
        f"Tersimpan di .env: AGENT_PROVIDER={chosen_provider}, AGENT_MODEL={chosen_model}"
    )
    return _init_model(chosen_provider, chosen_model)


def agent_llm(
    interactive: bool = True,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> Any:
    """Chat model untuk agent shorts/reels/tiktok (research & copy)."""
    return select_chat_model(
        interactive=interactive,
        provider=provider,
        model=model,
        temperature=temperature,
    )


def get_text_model(temperature: float = 0.7):
    """
    Satu-satunya jalur LLM teks di repo.

    Provider diambil dari AGENT_PROVIDER/AGENT_MODEL di .env (atau argumen),
    lalu diteruskan ke LangChain ``init_chat_model``. Mendukung semua provider
    dalam katalog: openai, gemini, anthropic, openroute, cloudflare, grok,
    meta/muse, glm, minmax, kimi, deepseek, mistral, ollama, dan lainnya.
    """
    return agent_llm(interactive=False, temperature=temperature)


def default_provider_model() -> tuple[str, Optional[str]]:
    """Convenience: (provider, first_model) dari discover_models()."""
    found = discover_models()
    if not found:
        return "", None
    provider = next(iter(found))
    return provider, (MODEL_CATALOG.get(provider) or [None])[0]


def list_available_models(
    provider: str | None = None, timeout: float = 5.0
) -> dict[str, list[str]]:
    """
    Cari model yang benar-benar tersedia.

    Sumber: daftar live dari API provider (bila key tersedia), lalu
    ``MODEL_CATALOG`` sebagai fallback. Ollama lokal ikut dicek via
    ``OLLAMA_HOST/api/tags``. Kegagalan jaringan diabaikan (fallback katalog).
    """
    import requests

    # Dahulukan provider dengan banyak model gratis (NIM, Groq, Gemini, Ollama, ...).
    providers = (
        [provider]
        if provider
        else sorted(MODEL_CATALOG, key=lambda p: (-free_model_count(p), p))
    )
    result: dict[str, list[str]] = {}
    for name in providers:
        models = list(MODEL_CATALOG.get(name, []))
        endpoint = _LIVE_ENDPOINTS.get(name)
        key_env = _PROVIDER_KEY_ENV.get(name, "")
        api_key = os.getenv(key_env, "").strip() if key_env else ""

        if endpoint and api_key:
            url, list_key, id_key = endpoint
            headers = {"Authorization": f"Bearer {api_key}"}
            if name == "anthropic":
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                live = [
                    str(item[id_key])
                    for item in payload.get(list_key, [])
                    if id_key in item
                ]
                if live:
                    models = sorted(set(live))[:60]
            except requests.RequestException, ValueError, KeyError, TypeError:
                pass

        if name == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if api_key:
                try:
                    url = "https://generativelanguage.googleapis.com/v1beta/models"
                    response = requests.get(
                        url, params={"key": api_key}, timeout=timeout
                    )
                    response.raise_for_status()
                    live = [
                        str(item["name"]).removeprefix("models/")
                        for item in response.json().get("models", [])
                        if "name" in item
                    ]
                    if live:
                        live = [m for m in live if _is_free(name, m)] + [
                            m for m in live if not _is_free(name, m)
                        ]
                        models = list(dict.fromkeys(live))[:60]
                except requests.RequestException, ValueError, KeyError, TypeError:
                    pass

        if name == "ollama":
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
            try:
                response = requests.get(f"{host}/api/tags", timeout=timeout)
                response.raise_for_status()
                live = [
                    str(item["name"])
                    for item in response.json().get("models", [])
                    if "name" in item
                ]
                if live:
                    models = sorted(set(live))[:60]
            except requests.RequestException, ValueError, KeyError, TypeError:
                pass

        if models:
            result[name] = _sort_free_first(name, models)[:60]
    return result


def select_provider_model(timeout: float = 5.0) -> tuple[str, str]:
    """
    Pilih provider/model secara interaktif.

    - Tampilkan model hasil pencarian live + katalog bernomor.
    - Ketik nomor untuk memilih.
    - Ketik manual ``provider/model`` (atau apa pun) bila tidak ada/ingin lain.
    """
    from backend.core.transcription import STT_PROVIDERS
    from backend.services.tts import TTS_PROVIDERS

    available = list_available_models(timeout=timeout)
    # Hanya provider LLM yang bisa dipilih sebagai AGENT_MODEL.
    options: list[tuple[str, str]] = [
        (name, model)
        for name, models in available.items()
        if PROVIDER_KIND.get(name) == "llm"
        for model in models
    ]

    if options:
        print("=== TTS (text -> speech) ===")
        print(f"  {', '.join(TTS_PROVIDERS)}  [TTS_PROVIDER di .env]")
        print("=== STT (speech -> text) ===")
        print(f"  {', '.join(STT_PROVIDERS)}  [STT_PROVIDER di .env]")
        print("=== LLM (chat) — pilih AGENT_MODEL ===")
        for index, (name, model) in enumerate(options, 1):
            label = " [GRATIS]" if _is_free(name, model) else ""
            print(f"  {index}. {name}/{model}{label}")
        print("  m. Input manual (provider/model)")
        choice = input(
            f"Pilih nomor (1-{len(options)}), 'm', atau langsung 'provider/model': "
        ).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        if "/" in choice:
            name, _, model = choice.partition("/")
            if name.strip() and model.strip():
                return name.strip(), model.strip()

    while True:
        value = (
            input(
                "Input provider/model (contoh: openai/gpt-4o-mini, ollama/llama3.3): "
            )
            .strip()
            .lstrip("\ufeff")
        )
        if not value:
            continue
        if "/" in value:
            name, _, model = value.partition("/")
            if name.strip() and model.strip():
                return name.strip(), model.strip()
        print("Format harus 'provider/model'. Coba lagi.")


def save_model_choice(provider: str, model: str, env_path: Path | None = None) -> Path:
    """Tulis AGENT_PROVIDER & AGENT_MODEL ke .env (baris lain tetap dipertahankan)."""
    path = env_path or ROOT_DIR / ".env"
    existing = (
        path.read_text(encoding="utf-8-sig").splitlines() if path.is_file() else []
    )
    wanted = {
        "AGENT_PROVIDER": provider.lstrip("\ufeff"),
        "AGENT_MODEL": model.lstrip("\ufeff"),
    }
    seen: set[str] = set()
    updated: list[str] = []
    for line in existing:
        key = line.split("=", 1)[0].strip()
        if key in wanted:
            updated.append(f"{key}={wanted[key]}")
            seen.add(key)
        else:
            updated.append(line)
    for key, value in wanted.items():
        if key not in seen:
            updated.append(f"{key}={value}")
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return path
