"""Bridge session frontend → JWT backend (project pribadi).

Frontend Better Auth sudah memverifikasi Google. Endpoint ini menerima email
dari session yang sudah terverifikasi (server-side) dan mengeluarkan JWT
dengan SECRET_KEY yang sama. Tidak menerima password/ID token dari client.
"""

import os
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.core.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_db
from backend.log import logger
from backend.models.user import User

GOOGLE_PASSWORD_SENTINEL = "GOOGLE_OAUTH"

router = APIRouter(prefix="/auth", tags=["Authentication"])


class BridgeRequest(BaseModel):
    email: EmailStr
    bridge_token: str


@router.post("/bridge", include_in_schema=False)
def bridge_session(request: BridgeRequest, db: Session = Depends(get_db)):
    expected = os.getenv("AUTH_BRIDGE_TOKEN", "").strip()
    allowed = {
        email.strip().lower()
        for email in os.getenv("OWNER_EMAILS", "").split(",")
        if email.strip()
    }
    email = str(request.email).lower().strip()
    if not expected or request.bridge_token != expected or email not in allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bridge ditolak."
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Owner sudah lolos whitelist + bridge token: provisioning aman.
        user = User(
            email=email,
            username=(email.split("@")[0] + "-" + secrets.token_hex(2))[:40],
            hashed_password=GOOGLE_PASSWORD_SENTINEL,
            referral_code=str(uuid.uuid7())[:8].upper(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"[Auth] User owner baru via bridge: {email}")

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer", "request_id": ""}
