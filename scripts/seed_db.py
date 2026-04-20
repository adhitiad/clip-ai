"""
Script Seed Database — AI Clipper
=================================
Membuat user contoh untuk setiap kombinasi role & plan:

  ROLES : OWNER | STAFF | USER
  PLANS :
    - OWNER  → plan khusus pemilik platform (tak terbatas)
    - STAFF  → plan khusus pengelola
    - free | premium | business | enterprise  → plan pelanggan

Jalankan:
    python scripts/seed_db.py

Opsi:
    --reset   Hapus semua user yang sudah ada sebelum seed
"""

import sys
import os
import argparse

# Pastikan root proyek ada di path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

import bcrypt

from utils.db import SessionLocal, init_db
from models.user import User, UserRole, UserPlan
from models.owner_setting import OwnerSetting
from log import logger


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ────────────── Data Seed ──────────────
SEED_USERS = [
    # ── OWNER (Pemilik Platform) ────────────────────────────────────────────
    {
        "email": "owner@clipai.dev",
        "username": "owner",
        "password": "Owner@12345",
        "role": UserRole.OWNER,
        "plan": UserPlan.OWNER,      # Plan khusus pemilik — akses tak terbatas
        "credits": 9999,
        "referral_code": "REF-OWNER",
    },
    # ── STAFF (Pengelola) ──────────────────────────────────────────────────
    {
        "email": "staff@clipai.dev",
        "username": "staff",
        "password": "Staff@12345",
        "role": UserRole.STAFF,
        "plan": UserPlan.STAFF,      # Plan khusus pengelola
        "credits": 9999,
        "referral_code": "REF-STAFF",
    },
    # ── USER — FREE ────────────────────────────────────────────────────────
    {
        "email": "user.free@clipai.dev",
        "username": "user_free",
        "password": "User@12345",
        "role": UserRole.USER,
        "plan": UserPlan.FREE,
        "credits": 3,
        "referral_code": "REF-USRFRE",
    },
    # ── USER — PREMIUM ─────────────────────────────────────────────────────
    {
        "email": "user.premium@clipai.dev",
        "username": "user_premium",
        "password": "User@12345",
        "role": UserRole.USER,
        "plan": UserPlan.PREMIUM,
        "credits": 100,
        "referral_code": "REF-USRPRE",
        "subscription_status": "active",
        "stripe_customer_id": "cus_seed_premium",
    },
    # ── USER — BUSINESS ────────────────────────────────────────────────────
    {
        "email": "user.business@clipai.dev",
        "username": "user_business",
        "password": "User@12345",
        "role": UserRole.USER,
        "plan": UserPlan.BUSINESS,
        "credits": 500,
        "referral_code": "REF-USRBIZ",
        "subscription_status": "active",
        "stripe_customer_id": "cus_seed_business",
    },
    # ── USER — ENTERPRISE ──────────────────────────────────────────────────
    {
        "email": "user.enterprise@clipai.dev",
        "username": "user_enterprise",
        "password": "User@12345",
        "role": UserRole.USER,
        "plan": UserPlan.ENTERPRISE,
        "credits": 9999,
        "referral_code": "REF-USRENT",
        "subscription_status": "active",
        "stripe_customer_id": "cus_seed_enterprise",
    },
]


def run_seed(reset: bool = False):
    init_db()
    db = SessionLocal()

    try:
        if reset:
            deleted = (
                db.query(User)
                .filter(User.email.in_([u["email"] for u in SEED_USERS]))
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info(f"🗑  Reset: {deleted} user seed lama dihapus.")

        created_count = 0
        owner_id = None

        for data in SEED_USERS:
            # Skip jika email sudah ada
            existing = db.query(User).filter(User.email == data["email"]).first()
            if existing:
                logger.warning(f"⏭  Skip (sudah ada): {data['email']}")
                if existing.role == UserRole.OWNER:
                    owner_id = existing.id
                continue

            user = User(
                email=data["email"],
                username=data.get("username"),
                hashed_password=hash_password(data["password"]),
                role=data["role"],
                plan=data["plan"],
                credits=data.get("credits", 3),
                used_credits=0,
                referral_code=data.get("referral_code"),
                stripe_customer_id=data.get("stripe_customer_id"),
                subscription_status=data.get("subscription_status", "inactive"),
            )
            db.add(user)
            db.flush()  # Dapatkan id sebelum commit

            if user.role == UserRole.OWNER:
                owner_id = user.id

            created_count += 1
            logger.info(
                f"✅ Dibuat: [{user.role.upper():8s}] [{user.plan.upper():10s}] {user.email}"
            )

        db.commit()

        # ── Buat/pastikan OwnerSetting untuk OWNER ──
        if owner_id:
            setting_exists = (
                db.query(OwnerSetting)
                .filter(OwnerSetting.owner_user_id == owner_id)
                .first()
            )
            if not setting_exists:
                setting = OwnerSetting(
                    owner_user_id=owner_id,
                    monitor_enabled=True,
                    monitor_refresh_seconds=30,
                    alert_queue_threshold=20,
                    alert_low_credit_threshold=1,
                    notify_email="owner@clipai.dev",
                )
                db.add(setting)
                db.commit()
                logger.info(f"⚙️  OwnerSetting dibuat untuk owner_id={owner_id}")

        logger.info(
            f"\n🎉 Seed selesai — {created_count} user baru dibuat dari {len(SEED_USERS)} konfigurasi.\n"
        )

        # ── Ringkasan semua user seed ──
        print("\n" + "=" * 65)
        print(f"  {'ROLE':<10} {'PLAN':<12} {'EMAIL':<35} {'PASSWORD'}")
        print("=" * 65)
        for u in SEED_USERS:
            role = u["role"].value.upper()
            plan = u["plan"].value.upper()
            print(f"  {role:<10} {plan:<12} {u['email']:<35} {u['password']}")
        print("=" * 65 + "\n")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seed gagal: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database AI Clipper")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Hapus user seed yang sudah ada sebelum membuat ulang",
    )
    args = parser.parse_args()
    run_seed(reset=args.reset)
