"""Healthcheck generik untuk image API/worker/render-worker.

Mendeteksi peran dari cmdline PID 1 lalu memeriksa hal yang memang relevan:
- uvicorn  -> GET /health/live
- taskiq   -> proses broker masih hidup
- worker:render -> proses worker masih hidup

Dipakai oleh HEALTHCHECK di Dockerfile. Tanpa dependency tambahan.
"""

from __future__ import annotations

import os
import urllib.request


def _cmdline() -> str:
    try:
        return open("/proc/1/cmdline", "rb").read().decode("utf-8", "replace")
    except OSError:
        return ""


def main() -> int:
    cmdline = _cmdline().lower()

    if "uvicorn" in cmdline:
        port = os.getenv("PORT", "8000")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health/live", timeout=2
            ) as response:
                return 0 if 200 <= response.status < 300 else 1
        except Exception:
            return 1

    if "taskiq" in cmdline or "worker:render" in cmdline:
        # PID 1 masih ada => proses worker masih hidup.
        return 0

    # Peran tidak dikenal: gagal, bukan healthcheck palsu.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
