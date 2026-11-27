"""Health publik untuk Docker healthcheck dan load balancer."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.core.rabbitmq_config import check_connection
from backend.utils.db import SessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def health_live() -> dict:
    """Proses hidup. Tidak menyentuh DB atau broker."""
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready() -> dict:
    """Siap menerima kerja: DB dan broker harus tersedia."""
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        pass
    broker = check_connection()
    if not db_ok or not broker["ok"]:
        raise HTTPException(
            status_code=503,
            detail={"database": db_ok, "broker": broker},
        )
    return {"status": "ready", "database": True, "broker": broker}
