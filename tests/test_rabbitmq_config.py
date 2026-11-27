"""Konfigurasi RabbitMQ (tanpa Redis) — murni, mudah di-test."""

import pytest

from backend.core.rabbitmq_config import (
    check_connection,
    get_rabbitmq_settings,
    resolve_url,
)


def test_default_and_override_url():
    assert resolve_url({}) == "amqp://guest:guest@localhost:5672//"
    custom = "amqp://user:pass@broker:5672/%2F"
    assert resolve_url({"RABBITMQ_URL": custom}) == custom


def test_invalid_scheme_rejected():
    with pytest.raises(ValueError, match="amqp"):
        resolve_url({"RABBITMQ_URL": "redis://localhost:6379/0"})


def test_taskiq_broker_uses_rabbitmq():
    from taskiq_aio_pika import AioPikaBroker

    from backend.core.taskiq_config import broker, dead_letter

    assert isinstance(broker, AioPikaBroker)
    assert broker.url.startswith("amqp://")

    from backend.core.task_results import PostgresResultBackend

    assert isinstance(broker.result_backend, PostgresResultBackend)
    assert dead_letter.name == "shorts-render-dlq"

    from taskiq.middlewares.smart_retry_middleware import SmartRetryMiddleware

    assert any(
        isinstance(middleware, SmartRetryMiddleware)
        for middleware in broker.middlewares
    )


def test_masked_url_hides_password():
    settings = get_rabbitmq_settings(
        {"RABBITMQ_URL": "amqp://user:rahasia@broker:5672//"}
    )
    assert "rahasia" not in settings.masked_url()
    assert "***" in settings.masked_url()


def test_check_connection_handles_failure(monkeypatch):
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1:1//")
    status = check_connection()
    assert status["ok"] is False
    assert status["provider"] == "rabbitmq"
