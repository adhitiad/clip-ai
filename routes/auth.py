import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from core.auth import get_db, get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user
from core.security import require_role
from models.user import User, UserPlan, UserRole
from pydantic import BaseModel, EmailStr
from log import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str = None
    referral_code: str = None # Code from the person who invited

class Token(BaseModel):
    access_token: str
    token_type: str

class BootstrapOwnerRequest(BaseModel):
    email: EmailStr
    bootstrap_token: str

class RoleUpdateRequest(BaseModel):
    email: EmailStr
    role: UserRole

class UserOut(BaseModel):
    email: str
    username: Optional[str]
    plan: UserPlan
    role: UserRole
    credits: int
    used_credits: int

    class Config:
        from_attributes = True

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    
    import uuid
    ref_code = str(uuid.uuid4())[:8].upper()
    
    # Check if this user was referred by someone
    referred_by_user = None
    if user_in.referral_code:
        referred_by_user = db.query(User).filter(User.referral_code == user_in.referral_code).first()

    new_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        plan=UserPlan.FREE,
        role=UserRole.USER,
        credits=3,
        referral_code=ref_code,
        referred_by_id=referred_by_user.id if referred_by_user else None
    )
    db.add(new_user)
    
    # Reward the referrer instantly
    if referred_by_user:
        referred_by_user.credits += 2 # SaaS Bonus Referral
        logger.info(f"👑 SaaS Bonus: {referred_by_user.email} got 2 credits for referring {new_user.email}")
        
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/bootstrap-owner", response_model=UserOut)
def bootstrap_owner(request: BootstrapOwnerRequest, db: Session = Depends(get_db)):
    expected_token = os.getenv("OWNER_BOOTSTRAP_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OWNER_BOOTSTRAP_TOKEN belum dikonfigurasi.",
        )
    if request.bootstrap_token != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap token tidak valid.")

    owner_exists = db.query(User).filter(User.role == UserRole.OWNER).first()
    if owner_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Owner sudah ada.")

    target_user = db.query(User).filter(User.email == request.email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")

    target_user.role = UserRole.OWNER
    db.commit()
    db.refresh(target_user)
    logger.warning("Bootstrap owner dijalankan untuk %s", target_user.email)
    return target_user


@router.post("/set-role", response_model=UserOut)
def set_user_role(
    request: RoleUpdateRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role([UserRole.OWNER])),
):
    target_user = db.query(User).filter(User.email == request.email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")

    if target_user.role == UserRole.OWNER and request.role != UserRole.OWNER:
        owner_count = db.query(User).filter(User.role == UserRole.OWNER).count()
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak bisa menurunkan role owner terakhir.",
            )

    target_user.role = request.role
    db.commit()
    db.refresh(target_user)
    return target_user

@router.post("/token", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
