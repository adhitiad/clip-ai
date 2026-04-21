import os
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

from routes.clips import router as clips_router
from routes.niche import router as niche_router
from routes.tools import router as tools_router
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.billing import router as billing_router
from routes.finance import router as finance_router
from routes.investment import router as investment_router
from log import logger

@asynccontextmanager
async def lifespan(_app: FastAPI):
    from utils.db import init_db
    from services.vector_store import init_vector_store

    init_db()
    init_vector_store()
    
    # Check Redis Connectivity (SaaS/Celery requirement)
    try:
        import redis
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        logger.info("Redis OK (Celery & SaaS Stats ready).")
    except Exception as e:
        logger.error(f"FATAL: Gagal koneksi Redis! Task async mungkin tidak jalan. Error: {e}")

    os.makedirs("temp", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    logger.info("Startup init selesai (DB, vector store, temp/models).")
    yield


app = FastAPI(title="AI Clipper Hub - Antigravity Edition", lifespan=lifespan)
PORT = int(os.getenv("PORT", 8000))

# Daftarkan router
app.include_router(auth_router)
app.include_router(clips_router)
app.include_router(niche_router)
app.include_router(tools_router)
app.include_router(dashboard_router)
app.include_router(billing_router)
app.include_router(finance_router)
app.include_router(investment_router)

if __name__ == "__main__":
    logger.info("AI Clipper Backend Server dimulai http://localhost:%s ...", PORT)
    uvicorn.run(app, host="127.0.0.1", port=PORT, reload=True)
