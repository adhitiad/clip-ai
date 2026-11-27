"""YouTube research + scheduler endpoints (lokal, dilindungi cron secret)."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from backend.core.auth import get_current_active_user
from backend.log import logger
from backend.models.user import User
from backend.utils.youtube_data import get_video_details, search_videos

router = APIRouter(prefix="/youtube", tags=["YouTube Research"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    max_results: int = Field(default=10, ge=1, le=50)


def _require_cron_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("YOUTUBE_CRON_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="YOUTUBE_CRON_SECRET belum diset.")
    if x_cron_secret != expected:
        raise HTTPException(status_code=401, detail="Cron secret tidak valid.")


@router.post("/search")
def youtube_search(
    request: SearchRequest, _current_user: User = Depends(get_current_active_user)
):
    """Riset video publik (butuh YOUTUBE_DATA_API_KEY)."""
    results = search_videos(request.query, request.max_results)
    return {"status": "success", "query": request.query, "results": results}


@router.get("/scheduler/status")
def scheduler_status(
    _current_user: User = Depends(get_current_active_user),
    _: None = Depends(_require_cron_secret),
):
    """Health check scheduler. Butuh JWT owner dan X-Cron-Secret."""
    return {
        "status": "ok",
        "youtube_data_key": bool(os.getenv("YOUTUBE_DATA_API_KEY", "").strip()),
    }


@router.post("/scheduler/collect")
def scheduler_collect(
    request: SearchRequest,
    _current_user: User = Depends(get_current_active_user),
    _: None = Depends(_require_cron_secret),
):
    """Kumpulkan kandidat video. Butuh JWT owner dan X-Cron-Secret."""
    videos = search_videos(request.query, request.max_results)
    details = get_video_details([video["video_id"] for video in videos])
    logger.info(f"[YouTubeScheduler] Mengumpulkan {len(videos)} kandidat.")
    return {
        "status": "success",
        "collected": len(videos),
        "candidates": videos,
        "details": details,
    }
