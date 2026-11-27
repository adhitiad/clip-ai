import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.core.env import load_env

load_env("backend")

from backend.log import logger
from backend.routes.agent import router as agent_router
from backend.routes.auth import router as auth_router
from backend.routes.bridge import router as bridge_router
from backend.routes.clips import router as clips_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.health import router as health_router
from backend.routes.niche import router as niche_router
from backend.routes.ops import router as ops_router
from backend.routes.revenue import router as revenue_router
from backend.routes.settings import router as settings_router
from backend.routes.tasks import router as tasks_router
from backend.routes.tools import router as tools_router
from backend.routes.youtube import router as youtube_router

# Pastikan folder download ada sebelum StaticFiles di-mount (test impor app langsung).
os.makedirs("download", exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from backend.services.vector_store import init_vector_store
    from backend.utils.db import init_db

    init_db()
    init_vector_store()

    # Check RabbitMQ Connectivity (broker Taskiq fallback)
    from backend.core.rabbitmq_config import check_connection, get_rabbitmq_settings

    broker_status = check_connection()
    if broker_status["ok"]:
        logger.info(f"RabbitMQ OK ({get_rabbitmq_settings().masked_url()}).")
    else:
        logger.error(
            f"FATAL: Gagal koneksi RabbitMQ! "
            f"Task async mungkin tidak jalan. Error: {broker_status['error']}"
        )

    for directory in ("temp", "models", "output", "logs", "download"):
        os.makedirs(directory, exist_ok=True)
    logger.info("Startup init selesai (DB, vector store, temp/models/output/download).")
    yield


app = FastAPI(
    title="Clip AI API",
    version="0.1.0",
    description=(
        "Backend pribadi Clip AI: agent shorts/reels/tiktok, klip, riset niche, "
        "tools, revenue, dan operasional. Satu user Google, tanpa billing."
    ),
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request, call_next):
    """Request ID (UUIDv7) + header keamanan untuk setiap respons."""
    from backend.core.request_id import new_request_id, set_request_id
    from backend.core.telemetry import log_event, start_trace

    rid = (
        request.headers.get("x-request-id", "").strip().lstrip("\ufeff")
        or new_request_id()
    )
    set_request_id(rid)
    trace = start_trace(request.headers.get("traceparent"), rid)

    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    response.headers["traceparent"] = trace.traceparent

    # Access log identitas per-request ke MongoDB (best-effort, non-blocking).
    try:
        from backend.services.access_logger import log_request

        await asyncio.to_thread(log_request, request, response, trace.traceparent, rid)
    except Exception as exc:
        logger.debug(f"[AccessLog] dilewati: {type(exc).__name__}")
    await asyncio.to_thread(
        log_event,
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Header berikut menutup temuan Nuclei info (COOP/COEP/HSTS/X-Permitted-Cross-Domain-Policies).
    # `credentialless` dipilih agar Swagger CDN tetap bisa dimuat di /docs.
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'",
    )
    if request.url.path in {"/docs", "/redoc", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' cdn.jsdelivr.net cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data:; connect-src 'self'"
        )
    return response


PORT = int(os.getenv("PORT", 8000))

# Daftarkan router
app.include_router(auth_router)
app.include_router(bridge_router)
app.include_router(health_router)
app.include_router(agent_router)
app.include_router(clips_router)
app.include_router(niche_router)
app.include_router(ops_router)
app.include_router(settings_router)
app.include_router(tasks_router)
app.include_router(tools_router)
app.include_router(dashboard_router)
app.include_router(revenue_router)
app.include_router(youtube_router)

# Serve thumbnail & video hasil download (download/ gitignored & dockerignored).
app.mount("/download", StaticFiles(directory="download"), name="download")


# ── OpenAPI hardening (CKV_OPENAPI_4/5/21) ──
# Global security: JWT Bearer, dengan opsi kosong `{}` untuk endpoint publik
# (health, /auth/google). Operasi yang butuh login tetap punya security sendiri
# lewat dependency get_current_active_user.
MAX_ARRAY_ITEMS = 500


def _limit_array_items(node: Any) -> None:
    """Tambahkan maxItems ke semua schema bertipe array (rekursif)."""
    if isinstance(node, dict):
        if node.get("type") == "array" and "maxItems" not in node:
            node["maxItems"] = MAX_ARRAY_ITEMS
        for value in node.values():
            _limit_array_items(value)
    elif isinstance(node, list):
        for item in node:
            _limit_array_items(item)


_original_openapi = app.openapi


def _hardened_openapi() -> dict:
    schema = _original_openapi()
    # `{}` adalah alternatif "tanpa otorisasi" agar endpoint publik tetap valid.
    schema.setdefault(
        "security",
        [{"OAuth2PasswordBearer": []}, {}],
    )
    _limit_array_items(schema.get("paths", {}))
    _limit_array_items(schema.get("components", {}).get("schemas", {}))
    return schema


app.openapi = _hardened_openapi

if __name__ == "__main__":
    logger.info("AI Clipper Backend Server dimulai http://localhost:%s ...", PORT)
    uvicorn.run(app, host="127.0.0.1", port=PORT, reload=True)
