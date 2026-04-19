import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from routes.clips import router as clips_router
from routes.niche import router as niche_router
from routes.tools import router as tools_router
from routes.auth import router as auth_router
from log import logger

@asynccontextmanager
async def lifespan(_app: FastAPI):
    from utils.db import init_db
    from services.vector_store import init_vector_store

    init_db()
    init_vector_store()
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

if __name__ == "__main__":
    logger.info("AI Clipper Backend Server dimulai http://localhost:%s ...", PORT)
    uvicorn.run(app, host="127.0.0.1", port=PORT, reload=True)
