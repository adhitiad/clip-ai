from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from utils.db import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)

    # Profile fields
    display_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    # Settings fields
    preferred_language = Column(String, default="id", nullable=False)
    timezone = Column(String, default="Asia/Jakarta", nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
