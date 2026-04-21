from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
from core.auth import get_db, get_current_active_user
from core.security import require_role
from models.user import User, UserPlan, UserRole
from models.investment import AppValuation, InvestorShare
from models.finance import Transaction
from datetime import datetime

router = APIRouter(prefix="/investment", tags=["Micro-Investment"])

# --- Schemas ---
class BuyInvestmentRequest(BaseModel):
    invest_amount: float

class InvestmentStatus(BaseModel):
    total_valuation: float
    founder_share_pct: float
    investor_share_pct: float
    available_share_pct: float
    remaining_share_pct: float
    currency: str

class ShareholderOut(BaseModel):
    email: str
    username: str
    role: str
    plan: str
    invested_amount: float
    share_pct: float
    created_at: str

# --- Helpers ---
def get_or_create_valuation(db: Session):
    valuation = db.query(AppValuation).first()
    if not valuation:
        valuation = AppValuation(
            total_valuation=500000000.0,
            founder_share_pct=53.0,
            available_share_pct=47.0,
            currency="IDR"
        )
        db.add(valuation)
        db.commit()
        db.refresh(valuation)
    return valuation

# --- Endpoints ---

@router.get("/status", response_model=InvestmentStatus)
def get_investment_status(db: Session = Depends(get_db)):
    val = get_or_create_valuation(db)
    
    # Calculate total share already bought by investors
    total_invested_pct = db.query(func.sum(InvestorShare.share_pct)).filter(InvestorShare.status == 'completed').scalar() or 0.0
    
    return {
        "total_valuation": val.total_valuation,
        "founder_share_pct": val.founder_share_pct,
        "investor_share_pct": total_invested_pct,
        "available_share_pct": val.available_share_pct,
        "remaining_share_pct": val.available_share_pct - total_invested_pct,
        "currency": val.currency
    }

@router.post("/buy")
def buy_investment(
    req: BuyInvestmentRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    val = get_or_create_valuation(db)
    
    # Calculate share percentage
    pct_to_buy = (req.invest_amount / val.total_valuation) * 100
    
    # Check availability
    total_invested_pct = db.query(func.sum(InvestorShare.share_pct)).filter(InvestorShare.status == 'completed').scalar() or 0.0
    remaining_pct = val.available_share_pct - total_invested_pct
    
    if pct_to_buy > remaining_pct:
        raise HTTPException(
            status_code=400, 
            detail=f"Saham tidak mencukupi. Sisa: {remaining_pct:.4f}%, Anda mencoba membeli: {pct_to_buy:.4f}%"
        )
    
    # 1. Simpan ke InvestorShare
    new_share = InvestorShare(
        user_id=current_user.id,
        invested_amount=req.invest_amount,
        share_pct=pct_to_buy,
        status="completed"
    )
    db.add(new_share)
    
    # 2. Update User Plan & Credits (Benefit)
    # Jika bukan owner atau enterprise, naikkan ke enterprise
    if current_user.plan not in [UserPlan.OWNER, UserPlan.ENTERPRISE]:
        current_user.plan = UserPlan.ENTERPRISE
        current_user.credits += 1000
    else:
        # Jika sudah enterprise/owner, tetap beri bonus credits
        current_user.credits += 1000
    
    # 3. Integrasi Keuangan: Catat sebagai income
    new_tx = Transaction(
        type="income",
        category="investment",
        amount=req.invest_amount,
        description=f"Investasi dari {current_user.email} ({pct_to_buy:.4f}%)"
    )
    db.add(new_tx)
    
    db.commit()
    return {"message": "Pembelian saham berhasil!", "share_pct": pct_to_buy, "new_plan": current_user.plan}

@router.get("/shareholders", response_model=List[ShareholderOut])
def get_shareholders(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role([UserRole.OWNER]))
):
    results = db.query(InvestorShare, User).join(User, InvestorShare.user_id == User.id).filter(InvestorShare.status == 'completed').all()
    
    out = []
    for share, user in results:
        out.append(ShareholderOut(
            email=user.email,
            username=user.username or "N/A",
            role=user.role,
            plan=user.plan,
            invested_amount=share.invested_amount,
            share_pct=share.share_pct,
            created_at=share.created_at.isoformat()
        ))
    return out
