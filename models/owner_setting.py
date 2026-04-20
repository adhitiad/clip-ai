from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from utils.db import Base


class OwnerSetting(Base):
    __tablename__ = "owner_settings"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, unique=True, index=True, nullable=False)

    monitor_enabled = Column(Boolean, default=True, nullable=False)
    monitor_refresh_seconds = Column(Integer, default=30, nullable=False)
    alert_queue_threshold = Column(Integer, default=20, nullable=False)
    alert_low_credit_threshold = Column(Integer, default=1, nullable=False)
    notify_email = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
