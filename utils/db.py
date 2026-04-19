import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Menggunakan koneksi PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/clip_ai")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    video_url = Column(String, index=True)
    topic = Column(String)
    start_time = Column(Integer)
    end_time = Column(Integer)
    title_en = Column(String)
    desc_en = Column(String)
    score = Column(Integer, default=0)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database PostgreSQL berhasil diinisialisasi via SQLAlchemy.")
    except Exception as e:
        print(f"⚠️ Gagal inisialisasi PostgreSQL (pastikan DATABASE_URL benar dan server menyala): {e}")

def save_clip(video_url: str, topic: str, start_time: int, end_time: int, title_en: str, desc_en: str) -> int:
    db = SessionLocal()
    try:
        new_clip = Clip(
            video_url=video_url,
            topic=topic,
            start_time=start_time,
            end_time=end_time,
            title_en=title_en,
            desc_en=desc_en,
            score=0
        )
        db.add(new_clip)
        db.commit()
        db.refresh(new_clip)
        return new_clip.id
    except Exception as e:
        print(f"Error saving to db: {e}")
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
