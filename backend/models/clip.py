from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from backend.utils.db import Base


class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    video_url = Column(String, index=True)
    topic = Column(String)
    start_time = Column(Integer)
    end_time = Column(Integer)
    title_en = Column(String)
    desc_en = Column(String)
    score = Column(Integer, default=0)
    user_id = Column(Integer, index=True, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to user if needed later
    # user_id = Column(Integer, ForeignKey("users.id"))
