"""Ringkasan pendapatan platform + saran AI (bukan billing/finance)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import get_current_active_user
from backend.core.rate_limit import check_rate_limit
from backend.log import logger
from backend.models.user import User
from backend.services.platform_revenue import collect_revenue, total_available
from backend.services.revenue_advice import AdviceUnavailable, generate_advice

router = APIRouter(
    prefix="/revenue",
    tags=["Revenue"],
    dependencies=[Depends(get_current_active_user)],
)

CURRENCY = "USD"


class PlatformRevenueOut(BaseModel):
    platform: str
    available: bool
    status: str
    amount: float | None = None
    currency: str | None = None
    period_start: str
    period_end: str
    source: str
    note: str = ""


class RevenueSummaryOut(BaseModel):
    status: str
    days: int
    platforms: list[PlatformRevenueOut]
    total_available: float
    currency: str
    generated_at: str
    note: str = ""


class RevenueAdviceOut(BaseModel):
    status: str
    provider: str
    model: str
    recommendations: list[str] = Field(default_factory=list)
    generated_at: str
    note: str = ""


@router.get("/summary", response_model=RevenueSummaryOut)
def revenue_summary(
    days: int = Query(28, ge=7, le=365),
    _current_user: User = Depends(get_current_active_user),
):
    """Ringkasan pendapatan dari adapter platform yang tersedia."""
    snapshots = collect_revenue(days)
    return RevenueSummaryOut(
        status="success",
        days=days,
        platforms=[PlatformRevenueOut(**snapshot.as_dict()) for snapshot in snapshots],
        total_available=total_available(snapshots, CURRENCY),
        currency=CURRENCY,
        generated_at=datetime.now(timezone.utc).isoformat(),
        note=(
            "Hanya platform dengan API pendapatan yang tersedia yang dijumlahkan. "
            "Platform tanpa data sengaja dilewati, bukan dianggap nol."
        ),
    )


@router.get("/advice", response_model=RevenueAdviceOut)
def revenue_advice(
    days: int = Query(28, ge=7, le=365),
    _current_user: User = Depends(get_current_active_user),
):
    """Saran peningkatan pendapatan dari model teks AGENT_* (satu jalur LLM)."""
    try:
        check_rate_limit("revenue-advice")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None

    snapshots = collect_revenue(days)
    try:
        advice = generate_advice(snapshots)
    except AdviceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:
        logger.warning(f"[Revenue] AI gagal: {type(exc).__name__}")
        raise HTTPException(
            status_code=502, detail="Gagal menghasilkan rekomendasi AI."
        ) from None
    return RevenueAdviceOut(**advice)
