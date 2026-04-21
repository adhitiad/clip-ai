from sqlalchemy import Column, Integer, String, Float, DateTime, func
from utils.db import Base

class Transaction(Base):
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # 'income' atau 'expense'
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
