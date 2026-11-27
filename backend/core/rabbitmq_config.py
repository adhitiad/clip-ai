"""Konfigurasi RabbitMQ — broker Taskiq & antrean AMQP (tanpa Redis)."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_URL = "amqp://guest:guest@localhost:5672//"


@dataclass(frozen=True)
class RabbitMQSettings:
    url: str
    broker_url: str

    def masked_url(self) -> str:
        parts = urlsplit(self.url)
        if parts.password:
            netloc = parts.netloc.replace(parts.password, "***", 1)
            return parts._replace(netloc=netloc).geturl()
        return self.url


def resolve_url(env: dict | None = None) -> str:
    source = env if env is not None else os.environ
    raw = str(source.get("RABBITMQ_URL", "")).strip() or DEFAULT_URL
    if not (raw.startswith("amqp://") or raw.startswith("amqps://")):
        raise ValueError("RABBITMQ_URL harus diawali amqp:// atau amqps://")
    return raw


def get_rabbitmq_settings(env: dict | None = None) -> RabbitMQSettings:
    url = resolve_url(env)
    return RabbitMQSettings(
        url=url,
        broker_url=url,
    )


def check_connection(settings: RabbitMQSettings | None = None) -> dict:
    """Ping broker via kombu (sudah jadi dependency Taskiq)."""
    settings = settings or get_rabbitmq_settings()
    try:
        from kombu import Connection

        with Connection(settings.broker_url) as connection:
            connection.connect()
            connected = connection.connected
        return {
            "ok": bool(connected),
            "provider": "rabbitmq",
            "version": None,
            "error": "" if connected else "koneksi ditolak",
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": "rabbitmq",
            "version": None,
            "error": str(exc),
        }
