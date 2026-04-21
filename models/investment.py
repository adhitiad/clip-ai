from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from utils.db import Base

class AppValuation(Base):
    __tablename__ = "app_valuations"

    id = Column(Integer, primary_key=True, index=True)
    total_valuation = Column(Float, default=500000000.0)
    founder_share_pct = Column(Float, default=53.0)
    available_share_pct = Column(Float, default=47.0)
    currency = Column(String, default="IDR")

class InvestorShare(Base):
    __tablename__ = "investor_shares"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    invested_amount = Column(Float, nullable=False)
    share_pct = Column(Float, nullable=False)
    status = Column(String, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to User
    user = relationship("User", back_populates="investments")
