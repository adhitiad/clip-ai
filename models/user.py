from enum import Enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime, func
from sqlalchemy.orm import relationship
from utils.db import Base

class UserPlan(str, Enum):
    # ── Plan internal (non-subscriber) ──────────────────
    OWNER = "owner"          # Pemilik platform — akses tak terbatas
    STAFF = "staff"          # Pengelola — akses pengelolaan
    # ── Plan pelanggan ───────────────────────────────────
    FREE = "free"
    PREMIUM = "premium"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class UserRole(str, Enum):
    OWNER = "owner"
    STAFF = "staff"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    
    plan = Column(SQLEnum(UserPlan, name="userplan", values_callable=lambda x: [e.value for e in x]), default=UserPlan.FREE)
    role = Column(SQLEnum(UserRole, name="userrole", values_callable=lambda x: [e.value for e in x]), default=UserRole.USER)
    
    # Quota system
    credits = Column(Integer, default=3)  # Free start with 3
    used_credits = Column(Integer, default=0)
    
    # SaaS Fields
    referral_code = Column(String, unique=True, index=True)
    referred_by_id = Column(Integer, nullable=True) # ID user yang mengajak
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    subscription_status = Column(String, default="inactive") # active, past_due, canceled
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    investments = relationship("InvestorShare", back_populates="user")
