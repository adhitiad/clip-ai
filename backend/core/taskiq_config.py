"""Broker Taskiq — RabbitMQ + result backend PostgreSQL/memory."""

from taskiq.middlewares.smart_retry_middleware import SmartRetryMiddleware
from taskiq_aio_pika import AioPikaBroker
from taskiq_aio_pika.queue import Queue

from backend.core.rabbitmq_config import get_rabbitmq_settings
from backend.core.task_results import PostgresResultBackend

settings = get_rabbitmq_settings()

# Task gagal setelah retry habis masuk DLQ, bukan hilang dari antrean.
dead_letter = Queue(name="shorts-render-dlq", durable=True)

broker = (
    AioPikaBroker(url=settings.broker_url, qos=1, dead_letter_queue=dead_letter)
    .with_result_backend(PostgresResultBackend())
    .with_middlewares(
        SmartRetryMiddleware(
            default_retry_count=2,
            default_retry_label=True,
            default_delay=3,
            use_jitter=True,
            use_delay_exponent=True,
            max_delay_exponent=30,
        )
    )
)
