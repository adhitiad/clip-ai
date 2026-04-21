from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from core.auth import get_db
from core.security import require_role
from models.user import User, UserRole
from models.finance import Transaction

router = APIRouter(
    prefix="/finance",
    tags=["Finance Tracking"],
    dependencies=[Depends(require_role([UserRole.OWNER]))]
)

# --- Schemas ---
class TransactionCreate(BaseModel):
    type: str  # 'income' or 'expense'
    category: str
    amount: float
    description: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    type: str
    category: str
    amount: float
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class FinanceSummary(BaseModel):
    total_income: float
    total_expense: float
    net_profit: float
    recent_transactions: List[TransactionOut]

# --- Endpoints ---

@router.get("/summary", response_model=FinanceSummary)
def get_finance_summary(db: Session = Depends(get_db)):
    # Calculate totals
    income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == 'income').scalar() or 0.0
    expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == 'expense').scalar() or 0.0
    
    # Get last 10 transactions
    recent = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Convert to schema-friendly objects (handling datetime to string)
    recent_out = []
    for t in recent:
        recent_out.append(TransactionOut(
            id=t.id,
            type=t.type,
            category=t.category,
            amount=t.amount,
            description=t.description,
            created_at=t.created_at.isoformat()
        ))

    return {
        "total_income": income,
        "total_expense": expense,
        "net_profit": income - expense,
        "recent_transactions": recent_out
    }

@router.post("/record", response_model=TransactionOut)
def record_transaction(tx_in: TransactionCreate, db: Session = Depends(get_db)):
    if tx_in.type not in ['income', 'expense']:
        raise HTTPException(status_code=400, detail="Type harus 'income' atau 'expense'")
    
    new_tx = Transaction(
        type=tx_in.type,
        category=tx_in.category,
        amount=tx_in.amount,
        description=tx_in.description
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    
    # Return with stringified date
    return TransactionOut(
        id=new_tx.id,
        type=new_tx.type,
        category=new_tx.category,
        amount=new_tx.amount,
        description=new_tx.description,
        created_at=new_tx.created_at.isoformat()
    )
