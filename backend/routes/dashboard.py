"""Dashboard pribadi — satu user, tanpa role/plan/kredit."""

import asyncio
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from backend.core.auth import get_current_active_user
from backend.core.models import ClipStat
from backend.models.clip import Clip
from backend.models.user import User
from backend.utils.db import SessionLocal

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _to_stats(clips: list[Clip]) -> list[ClipStat]:
    return [
        ClipStat(
            clip_id=clip.id,
            title=clip.title_en or clip.title_id or "",
            score=int(clip.score or 0),
            created_at=clip.created_at,
        )
        for clip in clips
    ]


def _get_clip_summary(db: Session) -> dict:
    """Agregasi skor clip memakai pandas."""
    clips = _to_stats(db.query(Clip).all())
    scores = pd.Series([clip.score for clip in clips], dtype=float)
    return {
        "total": int(scores.size),
        "average_score": float(scores.mean()) if scores.size else 0.0,
        "max_score": float(scores.max()) if scores.size else 0.0,
    }


def _overview_sync() -> tuple[list[dict], dict]:
    db = SessionLocal()
    try:
        clips = db.query(Clip).order_by(Clip.id.desc()).limit(5).all()
        recent = [
            {
                "id": clip.id,
                "title": clip.title_en or clip.title_id or "",
                "score": clip.score,
                "video_url": clip.video_url,
            }
            for clip in clips
        ]
        return recent, _get_clip_summary(db)
    finally:
        db.close()


def _history_sync(
    page: int, page_size: int, search: str, sort_by: str, sort_dir: str
) -> dict:
    db = SessionLocal()
    try:
        query = db.query(Clip)
        if search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Clip.title_en.ilike(pattern),
                    Clip.topic.ilike(pattern),
                    Clip.video_url.ilike(pattern),
                )
            )

        columns = {"id": Clip.id, "title": Clip.title_en, "score": Clip.score}
        column = columns[sort_by]
        order = column.asc() if sort_dir == "asc" else column.desc()
        total = query.count()
        clips = (
            query.order_by(order).offset((page - 1) * page_size).limit(page_size).all()
        )
        return {
            "total": total,
            "items": [
                {
                    "id": clip.id,
                    "title": clip.title_en or clip.topic or "",
                    "score": clip.score,
                    "start_time": clip.start_time,
                    "end_time": clip.end_time,
                    "video_url": clip.video_url,
                }
                for clip in clips
            ],
        }
    finally:
        db.close()


def _stats_sync() -> dict:
    db = SessionLocal()
    try:
        start = datetime.now(timezone.utc).date() - timedelta(days=6)
        stats = _to_stats(db.query(Clip).all())
        days = pd.Series(
            [
                clip.day_key()
                for clip in stats
                if clip.created_at and clip.day_key() >= start.isoformat()
            ],
            dtype=str,
        )
        counts = days.value_counts().sort_index()
        daily: dict[str, int] = {str(day): int(count) for day, count in counts.items()}
        values = np.array(list(daily.values()), dtype=float) if daily else np.array([])
        return {
            "daily": daily,
            "total": int(values.sum()) if values.size else 0,
            "peak": int(values.max()) if values.size else 0,
        }
    finally:
        db.close()


class DashboardUserOut(BaseModel):
    id: int
    email: str
    username: str | None = None


class ClipSummaryOut(BaseModel):
    total: int
    average_score: float
    max_score: float


class RecentClipOut(BaseModel):
    id: int
    title: str
    score: int | None = None
    video_url: str | None = None


class OverviewOut(BaseModel):
    status: str
    user: DashboardUserOut
    clips: ClipSummaryOut
    recent: list[RecentClipOut]
    generated_at: str


class HistoryItemOut(BaseModel):
    id: int
    title: str
    score: int | None = None
    start_time: int | None = None
    end_time: int | None = None
    video_url: str | None = None


class HistoryOut(BaseModel):
    status: str
    page: int
    page_size: int
    total: int
    search: str
    sort_by: str
    sort_dir: str
    items: list[HistoryItemOut]


class ProfileOut(BaseModel):
    status: str
    id: int
    email: str
    username: str | None = None
    joined_at: str | None = None


class StatsOut(BaseModel):
    status: str
    daily: dict[str, int]
    total: int
    peak: int


class HealthFlagOut(BaseModel):
    ok: bool


class DashboardHealthDetailOut(BaseModel):
    database: HealthFlagOut
    rabbitmq: HealthFlagOut


class DashboardHealthOut(BaseModel):
    status: str
    health: DashboardHealthDetailOut


@router.get("/overview", response_model=OverviewOut)
async def dashboard_overview(
    current_user: User = Depends(get_current_active_user),
):
    recent, summary = await asyncio.to_thread(_overview_sync)
    return {
        "status": "success",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
        },
        "clips": summary,
        "recent": recent,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history", response_model=HistoryOut)
async def dashboard_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default="", max_length=200),
    sort_by: str = Query(default="id", pattern="^(id|title|score)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    _current_user: User = Depends(get_current_active_user),
):
    result = await asyncio.to_thread(
        _history_sync, page, page_size, search, sort_by, sort_dir
    )
    return {
        "status": "success",
        "page": page,
        "page_size": page_size,
        "search": search,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        **result,
    }


@router.get("/profile", response_model=ProfileOut)
async def dashboard_profile(current_user: User = Depends(get_current_active_user)):
    return {
        "status": "success",
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "joined_at": current_user.created_at.isoformat()
        if current_user.created_at
        else None,
    }


@router.get("/stats", response_model=StatsOut)
async def dashboard_stats(
    _current_user: User = Depends(get_current_active_user),
):
    """Statistik 7 hari terakhir (jumlah clip per hari)."""
    result = await asyncio.to_thread(_stats_sync)
    return {"status": "success", **result}


def _health() -> dict:
    broker_ok = False
    try:
        from backend.core.rabbitmq_config import check_connection

        broker_ok = check_connection()["ok"]
    except Exception:
        pass
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        pass
    return {
        "database": {"ok": db_ok},
        "rabbitmq": {"ok": broker_ok},
    }


@router.get("/health", response_model=DashboardHealthOut)
async def dashboard_health(_current_user: User = Depends(get_current_active_user)):
    health = await asyncio.to_thread(_health)
    return {"status": "success", "health": health}
