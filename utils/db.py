import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from log import logger

# Menggunakan koneksi PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/clip_ai")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from models.clip import Clip
from models.owner_setting import OwnerSetting
from models.user_setting import UserSetting
from models.user import User
from models.finance import Transaction
from models.investment import AppValuation, InvestorShare

# Base.metadata.create_all akan memantau model yang diimpor

def _ensure_enum_values():
    """
    Memastikan semua value enum (userrole & userplan) tersedia di PostgreSQL.
    Aman di-skip untuk DB non-PostgreSQL.
    """
    if engine.dialect.name != "postgresql":
        return

    # { nama_enum_pg : [nilai yang harus ada] }
    required_values: dict[str, list[str]] = {
        "userrole": ["owner", "staff", "user"],
        "user_role_type": ["owner", "staff", "user"], # Fallback name
        "userplan": ["owner", "staff", "free", "premium", "business", "enterprise"],
        "user_plan_type": ["owner", "staff", "free", "premium", "business", "enterprise"], # Fallback name
    }

    try:
        with engine.begin() as conn:
            for enum_name, values in required_values.items():
                # Cek apakah tipe data enum ini ada di database
                type_exists = conn.exec_driver_sql(
                    "SELECT 1 FROM pg_type WHERE typname = %(ename)s",
                    {"ename": enum_name},
                ).fetchone()
                
                if not type_exists:
                    continue

                rows = conn.exec_driver_sql(
                    """
                    SELECT e.enumlabel
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = %(ename)s
                    """,
                    {"ename": enum_name},
                ).fetchall()

                existing = {r[0] for r in rows}
                for val in values:
                    if val not in existing:
                        # DDL tidak bisa diparameterkan — nilai dikontrol internal, aman
                        conn.exec_driver_sql(
                            f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{val}'"
                        )
                        logger.info(f"✅ Enum '{enum_name}' ditambah value '{val}'.")
    except Exception as e:
        logger.warning(f"⚠️ Tidak bisa memastikan nilai enum '{enum_name}': {e}")


def _ensure_users_columns():
    """
    Menambahkan kolom-kolom baru di tabel users yang mungkin belum ada
    (untuk database lama yang dibuat sebelum kolom ini ditambahkan ke model).
    """
    if engine.dialect.name != "postgresql":
        return

    # Daftar kolom yang harus ada: (nama, definisi SQL)
    required_columns = [
        ("username",             "VARCHAR UNIQUE"),
        ("hashed_password",      "VARCHAR"),
        ("plan",                 "userplan DEFAULT 'free'"),
        ("role",                 "userrole DEFAULT 'user'"),
        ("referral_code",        "VARCHAR UNIQUE"),
        ("referred_by_id",       "INTEGER"),
        ("stripe_customer_id",   "VARCHAR UNIQUE"),
        ("subscription_status",  "VARCHAR DEFAULT 'inactive'"),
        ("used_credits",         "INTEGER DEFAULT 0"),
        ("credits",              "INTEGER DEFAULT 3"),
        ("created_at",           "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at",           "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
    ]

    try:
        with engine.begin() as conn:
            table_exists = conn.exec_driver_sql(
                "SELECT to_regclass('public.users')"
            ).scalar()
            if not table_exists:
                return  # tabel belum ada, create_all akan membuatnya

            for col_name, col_def in required_columns:
                col_exists = conn.exec_driver_sql(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public' 
                      AND table_name = 'users' 
                      AND column_name = %(col)s
                    """,
                    {"col": col_name},
                ).fetchone()

                if not col_exists:
                    conn.exec_driver_sql(
                        f"ALTER TABLE public.users ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                    )
                    logger.info(f"✅ Kolom users.{col_name} berhasil ditambahkan.")
    except Exception as e:
        logger.warning(f"⚠️ Tidak bisa memastikan kolom users: {e}")


def _ensure_clip_user_id_column():
    """
    Menambahkan kolom clips.user_id pada database lama jika belum ada.
    """
    if engine.dialect.name != "postgresql":
        return
    try:
        with engine.begin() as conn:
            table_exists = conn.exec_driver_sql(
                "SELECT to_regclass('public.clips')"
            ).scalar()
            if not table_exists:
                return

            col_exists = conn.exec_driver_sql(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'clips' AND column_name = 'user_id'
                """
            ).fetchone()
            if not col_exists:
                conn.exec_driver_sql("ALTER TABLE clips ADD COLUMN user_id INTEGER")
                conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_clips_user_id ON clips (user_id)")
                logger.info("✅ Kolom clips.user_id berhasil ditambahkan.")
    except Exception as e:
        logger.warning(f"⚠️ Tidak bisa memastikan kolom clips.user_id: {e}")


def init_db():
    try:
        _ensure_enum_values()
        _ensure_users_columns()
        _ensure_clip_user_id_column()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database PostgreSQL berhasil diinisialisasi via SQLAlchemy.")
    except Exception as e:
        logger.error(f"⚠️ Gagal inisialisasi PostgreSQL (pastikan DATABASE_URL benar dan server menyala): {e}")


def save_clip(
    video_url: str,
    topic: str,
    start_time: int,
    end_time: int,
    title_en: str,
    desc_en: str,
    user_id: int | None = None,
) -> int:
    db = SessionLocal()
    try:
        new_clip = Clip(
            video_url=video_url,
            topic=topic,
            start_time=start_time,
            end_time=end_time,
            title_en=title_en,
            desc_en=desc_en,
            score=0,
            user_id=user_id,
        )
        db.add(new_clip)
        db.commit()
        db.refresh(new_clip)
        return new_clip.id
    except Exception as e:
        logger.error(f"Error saving to db: {e}")
        return 0
    finally:
        db.close()

def update_clip_score(clip_id: int, score_delta: int):
    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if clip:
            clip.score += score_delta
            db.commit()
    finally:
        db.close()

def get_clip_by_id(clip_id: int):
    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if clip:
            return {"topic": clip.topic, "title": clip.title_en, "desc": clip.desc_en, "score": clip.score}
        return None
    finally:
        db.close()

def get_top_clips(limit: int = 3):
    db = SessionLocal()
    try:
        clips = db.query(Clip).order_by(Clip.score.desc()).limit(limit).all()
        return [
            {"topic": c.topic, "title": c.title_en, "desc": c.desc_en, "score": c.score}
            for c in clips
        ]
    finally:
        db.close()
