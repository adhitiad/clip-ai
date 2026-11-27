"""Rate limit in-memory sederhana untuk endpoint AI (project pribadi, 1 user).

Tidak ada dependency baru. Thread-safe dengan Lock. Bisa di-reset lewat
``reset_buckets()`` di test.
"""

import os
import threading
import time
from collections import defaultdict, deque

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _limit() -> int:
    try:
        return max(1, int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "30")))
    except ValueError:
        return 30


def check_rate_limit(key: str) -> None:
    """Naikkan RuntimeError bila kuota per menit terlampaui."""
    now = time.monotonic()
    window = 60.0
    limit = _limit()
    with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RuntimeError(
                f"Rate limit terlampaui: maksimal {limit} request/menit."
            )
        bucket.append(now)


def reset_buckets() -> None:
    with _lock:
        _buckets.clear()
