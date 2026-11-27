"""Pengaturan pribadi & owner (satu user Google)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.core.auth import get_current_active_user, get_db
from backend.models.owner_setting import OwnerSetting
from backend.models.user import User
from backend.models.user_setting import UserSetting

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=[Depends(get_current_active_user)],
)


class UserSettingOut(BaseModel):
    id: int
    user_id: int
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    preferred_language: str
    timezone: str
    email_notifications: bool

    model_config = ConfigDict(from_attributes=True)


class UserSettingIn(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    preferred_language: str = "id"
    timezone: str = "Asia/Jakarta"
    email_notifications: bool = True


class OwnerSettingOut(BaseModel):
    id: int
    owner_user_id: int
    monitor_enabled: bool
    monitor_refresh_seconds: int
    alert_queue_threshold: int
    notify_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OwnerSettingIn(BaseModel):
    monitor_enabled: bool = True
    monitor_refresh_seconds: int = 30
    alert_queue_threshold: int = 20
    notify_email: str | None = None


def _user_setting(db: Session, user_id: int) -> UserSetting:
    row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if row is None:
        row = UserSetting(user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _owner_setting(db: Session, user_id: int) -> OwnerSetting:
    row = db.query(OwnerSetting).filter(OwnerSetting.owner_user_id == user_id).first()
    if row is None:
        row = OwnerSetting(owner_user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/me", response_model=UserSettingOut)
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _user_setting(db, current_user.id)


@router.patch("/me", response_model=UserSettingOut)
def update_my_settings(
    request: UserSettingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = _user_setting(db, current_user.id)
    for field, value in request.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.get("/owner", response_model=OwnerSettingOut)
def get_owner_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _owner_setting(db, current_user.id)


@router.patch("/owner", response_model=OwnerSettingOut)
def update_owner_settings(
    request: OwnerSettingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = _owner_setting(db, current_user.id)
    for field, value in request.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
