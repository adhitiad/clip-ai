"""ASGI guard untuk scan ZAP: hanya GET read-only yang mencapai backend.

``includePaths`` ZAP tidak cukup: OpenAPI import tetap bisa menyentuh endpoint
mahal/berefek samping. Guard ini menolak semua metode non-GET (kecuali bridge)
dan semua path di luar allowlist, lalu mencatat percobaan yang diblokir.

Dipakai oleh ``scripts/zap_auth_scan.py``; bukan untuk runtime produksi.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from backend.main import app as backend_app

ROOT = Path(__file__).resolve().parents[1]
ACCESS_LOG = ROOT / "temp" / "zap-access.log"
BLOCK_LOG = ROOT / "temp" / "zap-blocked.log"

SAFE_GET_EXACT = {
    "/auth/me",
    "/clips",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/ops/tasks",
    "/ops/queue",
    "/ops/workers",
    "/ops/cache",
    "/ops/traces",
    "/ops/export",
    "/ops/audit",
    "/settings/me",
    "/settings/owner",
    "/tools/providers",
    "/tools/platforms",
    "/tools/calibration",
    "/tools/model-status",
    "/dashboard/overview",
    "/dashboard/history",
    "/dashboard/profile",
    "/dashboard/stats",
    "/dashboard/health",
    "/youtube/scheduler/status",
}
SAFE_GET_PREFIXES = ("/clips/", "/tasks/")
SAFE_POST_EXACT = {"/auth/bridge"}


def _log(path: Path, line: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _allowed(method: str, path: str) -> bool:
    if method == "POST":
        return path in SAFE_POST_EXACT
    if method != "GET":
        return False
    if path in SAFE_GET_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in SAFE_GET_PREFIXES)


async def _reject(send) -> None:
    body = json.dumps({"detail": "blocked by ZAP safe wrapper"}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def app(scope, receive, send) -> None:
    if scope["type"] != "http":
        await backend_app(scope, receive, send)
        return

    method = scope.get("method", "GET")
    path = scope.get("path", "/")
    if not _allowed(method, path):
        _log(BLOCK_LOG, f"{method} {path}")
        await _reject(send)
        return

    status = 0

    async def send_wrapper(message) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        await send(message)

    try:
        await backend_app(scope, receive, send_wrapper)
    finally:
        _log(ACCESS_LOG, f"{method} {path} {status}")


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ZAP_SCAN_PORT", "8011")))
