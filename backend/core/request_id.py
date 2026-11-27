"""Request ID lintas API → Taskiq worker (T-17).

Menggunakan ``contextvars`` agar aman untuk async FastAPI dan thread worker.
ID memakai UUIDv7 (stdlib Python 3.14).
"""

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return str(uuid.uuid7())


def set_request_id(value: str) -> None:
    _request_id.set(value.lstrip("\ufeff"))


def get_request_id() -> str:
    return _request_id.get()
