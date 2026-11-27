"""Deteksi jumlah worker Taskiq dari inti fisik mesin.

Hasil genap untuk 2+ core (2, 4, 6, 8, ...) dan **1** bila mesin hanya punya
1 core fisik. Override dengan `TASKIQ_WORKERS` bila ingin jumlah tertentu.
"""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def physical_cores() -> int:
    try:
        import psutil

        count = psutil.cpu_count(logical=False) or 0
    except Exception:
        count = 0
    if count < 1:
        count = os.cpu_count() or 1
    return max(1, int(count))


def recommended_workers() -> int:
    raw = os.getenv("TASKIQ_WORKERS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    cores = physical_cores()
    if cores <= 1:
        return 1
    return cores if cores % 2 == 0 else cores + 1


def configured_workers() -> int:
    raw = os.getenv("TASKIQ_WORKERS", "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else 0
