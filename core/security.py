from typing import List
from fastapi import Depends, HTTPException, status
from core.auth import get_current_active_user, get_db
from models.user import User, UserRole, UserPlan
from sqlalchemy.orm import Session
from log import logger

def require_role(allowed_roles: List[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} tidak memiliki izin untuk akses ini. Diperlukan salah satu dari: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

def require_plan(min_plan: UserPlan):
    # Urutan plan untuk pengecekan level
    plan_order = {
        UserPlan.FREE: 0,
        UserPlan.PREMIUM: 1,
        UserPlan.BUSINESS: 2,
        UserPlan.ENTERPRISE: 3
    }
    
    async def plan_checker(current_user: User = Depends(get_current_active_user)):
        if plan_order[current_user.plan] < plan_order[min_plan]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Fitur ini memerlukan plan minimum {min_plan.value}. Plan Anda saat ini: {current_user.plan.value}"
            )
        return current_user
    return plan_checker

# Dependency untuk mengecek kecukupan kredit
async def check_credits(current_user: User = Depends(get_current_active_user)):
    if current_user.credits <= 0:
        logger.warning(f"Akses ditolak: User {current_user.email} kehabisan kredit.")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Kredit Anda habis. Silakan upgrade plan atau isi ulang kredit Anda."
        )
    return current_user

# Helper untuk memotong credit
def deduct_credit(db: Session, user: User, amount: int = 1):
    try:
        user.credits -= amount
        user.used_credits += amount
        db.commit()
        db.refresh(user)
        logger.info(f"Kredit dipotong: {user.email} (-{amount}). Sisa: {user.credits}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal memotong kredit untuk {user.email}: {str(e)}")
        return False
