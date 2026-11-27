from sqlalchemy import Column, Integer, String, DateTime, func
from backend.utils.db import Base


class User(Base):
    """Project pribadi — satu tipe user (pemilik). Tanpa role/plan/kredit."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)  # sentinel GOOGLE_OAUTH
    google_sub = Column(String, unique=True, index=True, nullable=True)

    referral_code = Column(String, unique=True, index=True)
    referred_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

