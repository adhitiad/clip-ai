"""Autentikasi Google-only — tanpa password."""

import os
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from backend.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    get_db,
)
from backend.core.env import load_env
from backend.log import logger
from backend.models.user import User

load_env("backend")
router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_PASSWORD_SENTINEL = "GOOGLE_OAUTH"
OWNER_EMAILS = {
    email.strip().lower()
    for email in os.getenv("OWNER_EMAILS", "").split(",")
    if email.strip()
}


class GoogleLoginRequest(BaseModel):
    id_token: str
    referral_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class BootstrapOwnerRequest(BaseModel):
    email: EmailStr
    bootstrap_token: str


class UserOut(BaseModel):
    email: str
    username: Optional[str]

    model_config = ConfigDict(from_attributes=True)


def verify_google_token(credential: str) -> dict:
    """Verifikasi Google ID token; kembalikan klaim (email, sub, ...)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_CLIENT_ID belum dikonfigurasi.",
        )
    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token tidak valid.",
        ) from exc
    if not claims.get("email") or not claims.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email Google belum terverifikasi.",
        )
    return claims


@router.post("/google", response_model=Token)
def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Login/daftar otomatis lewat Google ID token. Tidak ada password."""
    claims = verify_google_token(request.id_token)
    email = str(claims["email"]).lower().strip()
    google_sub = str(claims.get("sub", ""))

    if OWNER_EMAILS and email not in OWNER_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ini tidak diizinkan mengakses project pribadi.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        import uuid

        referred_by = None
        if request.referral_code:
            referred_by = (
                db.query(User)
                .filter(User.referral_code == request.referral_code)
                .first()
            )
        user = User(
            email=email,
            username=(email.split("@")[0] + "-" + secrets.token_hex(2))[:40],
            hashed_password=GOOGLE_PASSWORD_SENTINEL,
            google_sub=google_sub,
            referral_code=str(uuid.uuid7())[:8].upper(),
            referred_by_id=referred_by.id if referred_by else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"[Auth] User Google baru: {email}")

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
