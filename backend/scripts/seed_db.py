"""Seed project pribadi: tepat satu user (email pertama di OWNER_EMAILS)."""

import os

from backend.core.env import load_env
from backend.log import logger
from backend.models.user import User
from backend.utils.db import SessionLocal, init_db

load_env("backend")

OWNER_EMAILS = [
    email.strip().lower()
    for email in os.getenv("OWNER_EMAILS", "").split(",")
    if email.strip()
]


def run_seed(reset: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if reset:
            deleted = db.query(User).delete()
            db.commit()
            logger.info(f"Seed: {deleted} user lama dihapus.")

        if not OWNER_EMAILS:
            logger.warning("OWNER_EMAILS kosong; tidak ada user yang dibuat.")
            return

        email = OWNER_EMAILS[0]
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                username=email.split("@")[0],
                hashed_password="GOOGLE_OAUTH",
                referral_code="OWNER01",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"User pribadi: {user.email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    run_seed(reset=args.reset)
