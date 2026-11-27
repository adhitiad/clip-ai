"""Kesehatan provider LLM — circuit breaker in-memory (tanpa Redis)."""

import time

FAILURE_THRESHOLD = 2
COOLDOWN_SECONDS = 60

_failures: dict[str, int] = {}
_disabled_until: dict[str, float] = {}


def record_failure(provider: str) -> bool:
    """Catat kegagalan; kembalikan True bila provider masuk cooldown."""
    name = provider.strip().lower()
    count = _failures.get(name, 0) + 1
    _failures[name] = count
    if count >= FAILURE_THRESHOLD:
        _disabled_until[name] = time.monotonic() + COOLDOWN_SECONDS
        return True
    return False


def record_success(provider: str) -> None:
    name = provider.strip().lower()
    _failures.pop(name, None)
    _disabled_until.pop(name, None)


def is_healthy(provider: str) -> bool:
    name = provider.strip().lower()
    until = _disabled_until.get(name, 0.0)
    if until and time.monotonic() < until:
        return False
    if until:
        _disabled_until.pop(name, None)
        _failures.pop(name, None)
    return True


def health_state(provider: str) -> dict:
    name = provider.strip().lower()
    return {
        "healthy": is_healthy(name),
        "failures": _failures.get(name, 0),
        "retry_after": max(0, round(_disabled_until.get(name, 0.0) - time.monotonic()))
        if name in _disabled_until
        else 0,
    }


def reset() -> None:
    _failures.clear()
    _disabled_until.clear()
