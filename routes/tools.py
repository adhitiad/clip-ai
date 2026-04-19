"""
routes/tools.py
================
Endpoint untuk fitur tambahan:

  POST /tools/dub          → AI Voice-Over Dubbing satu video klip
  POST /tools/viral-score  → Prediksi skor viral sebelum render
  GET  /tools/model-status → Status model ML (jumlah training data, dll)
  POST /tools/feedback     → Record performa nyata klip untuk continuous learning
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from core.security import require_plan, require_role
from models.user import UserPlan, UserRole, User

router = APIRouter(prefix="/tools", tags=["AI Tools"])
ALLOWED_DUB_ROOT = Path(os.getenv("DUB_ALLOWED_ROOT", "temp")).resolve()


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class DubRequest(BaseModel):
    video_path: str = Field(..., description="Path absolut ke file video MP4 yang sudah dirender")
    target_lang: str = Field(default="id", description="'id' untuk Indonesia, 'en' untuk English")
    keep_original_audio: float = Field(default=0.1, ge=0.0, le=1.0,
        description="Volume audio asli (0=mute, 0.1=ambient, 1.0=full)")
    output_path: Optional[str] = Field(default="", description="Path output; kosong = auto")


class ViralScoreRequest(BaseModel):
    title: str = Field(..., description="Judul klip (Indonesia atau English)")
    description: str = Field(default="", description="Deskripsi/hook klip")
    start_time: float = Field(default=0, description="Detik mulai klip")
    end_time: float = Field(default=60, description="Detik selesai klip")
    has_broll: bool = Field(default=False, description="Apakah ada B-Roll query")
    audio_path: str = Field(default="", description="Path audio untuk analisis energi")
    threshold: float = Field(default=6.5, ge=1.0, le=10.0,
        description="Threshold minimum skor untuk direkomendasikan render")


class PerformanceFeedback(BaseModel):
    clip_id: int
    actual_views: int = 0
    actual_likes: int = 0
    actual_shares: int = 0


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post("/dub")
async def dub_video(
    request: DubRequest, 
    _current_user: User = Depends(require_plan(UserPlan.PREMIUM))
):
    """
    AI Voice-Over Auto Dubbing.

    Pipeline:
      1. Transkripsi audio asli (Groq Whisper)
      2. Terjemahan ke target bahasa (LLaMA)
      3. Generate suara baru (ElevenLabs / gTTS fallback)
      4. Gabung audio ke video (FFmpeg)

    Return path ke video hasil dubbing.
    """
    video_path = Path(request.video_path).expanduser().resolve()
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"File tidak ditemukan: {video_path}")
    if not _is_within_root(video_path, ALLOWED_DUB_ROOT):
        raise HTTPException(
            status_code=403,
            detail=f"video_path harus berada di dalam direktori yang diizinkan: {ALLOWED_DUB_ROOT}",
        )

    output_path = ""
    if request.output_path:
        resolved_output = Path(request.output_path).expanduser().resolve()
        if not _is_within_root(resolved_output, ALLOWED_DUB_ROOT):
            raise HTTPException(
                status_code=403,
                detail=f"output_path harus berada di dalam direktori yang diizinkan: {ALLOWED_DUB_ROOT}",
            )
        output_path = str(resolved_output)

    from services.dubbing import dub_video_clip

    result_path = dub_video_clip(
        video_path=str(video_path),
        target_lang=request.target_lang,
        output_path=output_path,
        keep_original_audio=request.keep_original_audio,
    )

    if not result_path:
        raise HTTPException(status_code=500, detail="Dubbing gagal. Cek log server.")

    return {
        "status": "success",
        "dubbed_video": result_path,
        "target_language": request.target_lang,
        "original_video": str(video_path),
        "message": f"Dubbing ke '{request.target_lang}' berhasil.",
    }


@router.post("/viral-score")
async def predict_viral(
    request: ViralScoreRequest,
    _current_user: User = Depends(require_plan(UserPlan.BUSINESS))
):
    """
    Prediksi skor viral (1-10) sebelum render menggunakan ML model.

    Cold start: gunakan rule-based scoring.
    Setelah 50+ klip terdata: model GradientBoosting aktif.

    Skor >= 6.5 direkomendasikan untuk dirender.
    """
    from services.viral_predictor import predict_viral_score

    clip_metadata = {
        "title_en": request.title,
        "title_id": request.title,
        "desc_en": request.description,
        "desc_id": request.description,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "broll_query": "yes" if request.has_broll else "",
    }

    result = predict_viral_score(
        clip_metadata=clip_metadata,
        audio_path=request.audio_path,
        threshold=request.threshold,
    )

    return {
        "status": "success",
        "title": request.title,
        "viral_score": result["ml_viral_score"],
        "should_render": result["ml_should_render"],
        "confidence_mode": result["ml_confidence"],
        "threshold": request.threshold,
        "features": {
            "duration_score":     round(result["ml_features"][0], 3),
            "title_power_words":  int(result["ml_features"][1]),
            "desc_power_words":   int(result["ml_features"][2]),
            "title_length_score": round(result["ml_features"][3], 3),
            "has_broll":          bool(result["ml_features"][4]),
            "audio_energy":       round(result["ml_features"][5], 3),
            "face_count_norm":    round(result["ml_features"][6], 3),
            "hook_ratio":         round(result["ml_features"][7], 3),
        },
        "recommendation": (
            "RENDER — konten ini berpotensi viral!" if result["ml_should_render"]
            else f"SKIP — skor {result['ml_viral_score']:.1f} < threshold {request.threshold}. "
                 "Coba perbaiki judul dengan lebih banyak power words."
        ),
    }


@router.get("/model-status")
async def model_status(
    _current_user: User = Depends(require_role([UserRole.OWNER]))
):
    """
    Cek status model ML Viral Predictor:
    - Berapa sample training yang sudah ada
    - Apakah model sudah dilatih
    - Kapan terakhir dilatih
    """
    from services.viral_predictor import DATA_PATH, MODEL_PATH, RETRAIN_EVERY

    # Count training samples
    sample_count = 0
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            sample_count = sum(1 for line in f if line.strip())

    model_exists = os.path.exists(MODEL_PATH)
    model_size   = os.path.getsize(MODEL_PATH) if model_exists else 0
    model_mtime  = os.path.getmtime(MODEL_PATH) if model_exists else None

    import datetime
    last_trained = (
        datetime.datetime.fromtimestamp(model_mtime).isoformat()
        if model_mtime else None
    )

    next_retrain = RETRAIN_EVERY - (sample_count % RETRAIN_EVERY) if sample_count > 0 else RETRAIN_EVERY

    return {
        "status": "success",
        "model": {
            "trained": model_exists,
            "last_trained": last_trained,
            "model_size_kb": round(model_size / 1024, 1),
            "confidence_mode": "ml_model" if model_exists else "rule_based",
        },
        "training_data": {
            "total_samples": sample_count,
            "samples_until_retrain": next_retrain if model_exists else RETRAIN_EVERY - sample_count,
            "retrain_interval": RETRAIN_EVERY,
        },
        "message": (
            f"Model aktif dengan {sample_count} samples. Retrain dalam {next_retrain} klip lagi."
            if model_exists
            else f"Rule-based mode. Butuh {RETRAIN_EVERY} samples untuk training ML pertama "
                 f"(sekarang: {sample_count})."
        ),
    }


@router.post("/feedback")
async def record_feedback(
    request: PerformanceFeedback,
    _current_user: User = Depends(require_plan(UserPlan.PREMIUM))
):
    """
    Record performa nyata klip setelah dipublish.
    Data ini digunakan untuk continuous learning model ML.

    Panggil endpoint ini setelah mendapat data views/likes dari platform.
    """
    from services.viral_predictor import record_actual_performance

    record_actual_performance(
        clip_id=request.clip_id,
        actual_views=request.actual_views,
        actual_likes=request.actual_likes,
        actual_shares=request.actual_shares,
    )

    return {
        "status": "success",
        "clip_id": request.clip_id,
        "message": f"Performa klip {request.clip_id} tercatat. Digunakan untuk meningkatkan model ML.",
    }
