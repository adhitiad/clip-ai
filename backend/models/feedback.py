"""Feedback performa nyata — analitik kalibrasi, bukan training model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.utils.db import Base


class PerformanceFeedbackRecord(Base):
    __tablename__ = "performance_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clip_id: Mapped[int] = mapped_column(Integer, index=True)
    actual_views: Mapped[int] = mapped_column(Integer, default=0)
    actual_likes: Mapped[int] = mapped_column(Integer, default=0)
    actual_shares: Mapped[int] = mapped_column(Integer, default=0)
    predicted_score: Mapped[float] = mapped_column(Float, default=0.0)
    real_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
