"""
routes/tools.py
================
Endpoint untuk fitur tambahan:

  POST /tools/dub          → AI Voice-Over Dubbing satu video klip
  POST /tools/viral-score  → Prediksi skor viral sebelum render
  GET  /tools/model-status → Status scoring (rule-based, tanpa model)
  GET  /tools/providers    → Katalog provider/model dari backend (sumber tunggal UI)
  GET  /tools/platforms    → Daftar platform shorts dari backend (sumber tunggal UI)
  POST /tools/feedback     → Catat performa nyata klip untuk analitik
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import get_current_active_user
from backend.core.rate_limit import check_rate_limit
from backend.core.security import require_owner
from backend.core.transcription import STT_PROVIDERS
from backend.core.validation import (
    MAX_SCRIPT_TEXT,
    resolve_confined_path,
    validate_lang,
    validate_text,
)
from backend.models.user import User
from backend.routes.agent import Platform
from backend.services.model_discovery import (
    FREE_MODELS,
    MODEL_CATALOG,
    PROVIDER_KIND,
    provider_metadata,
)
from backend.services.tts import TTS_PROVIDERS

router = APIRouter(prefix="/tools", tags=["AI Tools"])
ALLOWED_DUB_ROOT = Path(os.getenv("DUB_ALLOWED_ROOT", "temp")).resolve()


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────


class DubRequest(BaseModel):
    video_path: str = Field(
        ..., description="Path absolut ke file video MP4 yang sudah dirender"
    )
    target_lang: str = Field(
        default="id", description="'id' untuk Indonesia, 'en' untuk English"
    )
    keep_original_audio: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Volume audio asli (0=mute, 0.1=ambient, 1.0=full)",
    )
    output_path: Optional[str] = Field(
        default="", description="Path output; kosong = auto"
    )
    script_text: str = Field(
        default="",
        max_length=MAX_SCRIPT_TEXT,
        description="Naskah dubbing opsional; bila diisi, transkripsi dilewati",
    )


class ViralScoreRequest(BaseModel):
    title: str = Field(..., description="Judul klip (Indonesia atau English)")
    description: str = Field(default="", description="Deskripsi/hook klip")
    start_time: float = Field(default=0, description="Detik mulai klip")
    end_time: float = Field(default=60, description="Detik selesai klip")
    has_broll: bool = Field(default=False, description="Apakah ada B-Roll query")
    audio_path: str = Field(default="", description="Path audio untuk analisis energi")
    threshold: float = Field(
        default=6.5,
        ge=1.0,
        le=10.0,
        description="Threshold minimum skor untuk direkomendasikan render",
    )


class PerformanceFeedback(BaseModel):
    clip_id: int
    actual_views: int = 0
    actual_likes: int = 0
    actual_shares: int = 0


# ─── RESPONSE MODELS ───────────────────────────────────────────────────────────


class DubOut(BaseModel):
    status: str
    dubbed_video: str
    target_language: str
    original_video: str
    message: str


class ViralFeaturesOut(BaseModel):
    duration_score: float
    title_power_words: int
    desc_power_words: int
    title_length_score: float
    has_broll: bool
    audio_energy: float
    audio_pitch: float
    face_emotion: float
    face_count_norm: float
    hook_ratio: float


class ViralScoreOut(BaseModel):
    status: str
    title: str
    viral_score: float
    should_render: bool
    confidence_mode: str
    threshold: float
    features: ViralFeaturesOut
    recommendation: str


class ProviderOut(BaseModel):
    id: str
    kind: str
    free: bool
    models: list[str]
    latency_hint: str
    cost_tier: str
    healthy: bool


class ProvidersOut(BaseModel):
    status: str
    providers: list[ProviderOut]
    tts: list[str]
    stt: list[str]


class PlatformsOut(BaseModel):
    status: str
    platforms: list[str]
    default: str


class ModelStateOut(BaseModel):
    trained: bool
    enabled: bool
    confidence_mode: str


class ModelStatusOut(BaseModel):
    status: str
    model: ModelStateOut
    message: str


class FeedbackOut(BaseModel):
    status: str
    clip_id: int
    message: str


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────


@router.post("/dub", response_model=DubOut)
async def dub_video(
    request: DubRequest, _current_user: User = Depends(get_current_active_user)
):
    """
    AI Voice-Over Auto Dubbing.

    Pipeline:
      1. Transkripsi audio asli (Whisper via REST)
      2. Terjemahan ke target bahasa (LLaMA)
      3. Generate suara baru (Cartesia / Camb AI / gTTS fallback)
      4. Gabung audio ke video (FFmpeg)

    Return path ke video hasil dubbing.
    """
    try:
        check_rate_limit("dub")
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None
    try:
        target_lang = validate_lang(request.target_lang)
        script_text = validate_text(
            request.script_text, "script_text", MAX_SCRIPT_TEXT, min_length=0
        )
        video_path = resolve_confined_path(request.video_path, ALLOWED_DUB_ROOT)
        output_path = (
            str(resolve_confined_path(request.output_path, ALLOWED_DUB_ROOT))
            if request.output_path
            else ""
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="File video tidak ditemukan.")

    from backend.services.dubbing import dub_video_clip

    result_path = await asyncio.to_thread(
        dub_video_clip,
        video_path=str(video_path),
        target_lang=target_lang,
        output_path=output_path,
        keep_original_audio=request.keep_original_audio,
        script_text=script_text,
    )

    if not result_path:
        raise HTTPException(status_code=500, detail="Dubbing gagal. Cek log server.")

    return {
        "status": "success",
        "dubbed_video": result_path,
        "target_language": target_lang,
        "original_video": str(video_path),
        "message": f"Dubbing ke '{target_lang}' berhasil.",
    }


@router.post("/viral-score", response_model=ViralScoreOut)
async def predict_viral(
    request: ViralScoreRequest,
    _current_user: User = Depends(get_current_active_user),
):
    """
    Prediksi skor viral (1-10) sebelum render (rule-based, tanpa model ML).

    Skor >= threshold direkomendasikan untuk dirender.
    """
    from backend.services.viral_predictor import predict_viral_score

    clip_metadata = {
        "title_en": request.title,
        "title_id": request.title,
        "desc_en": request.description,
        "desc_id": request.description,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "broll_query": "yes" if request.has_broll else "",
    }

    result = await asyncio.to_thread(
        predict_viral_score,
        clip_metadata=clip_metadata,
        audio_path=request.audio_path,
        threshold=request.threshold,
    )
    features = result["ml_features"]

    return {
        "status": "success",
        "title": request.title,
        "viral_score": result["ml_viral_score"],
        "should_render": result["ml_should_render"],
        "confidence_mode": result["ml_confidence"],
        "threshold": result["ml_threshold_used"],
        "features": {
            "duration_score": round(features[0], 3),
            "title_power_words": int(features[1]),
            "desc_power_words": int(features[2]),
            "title_length_score": round(features[3], 3),
            "has_broll": bool(features[4]),
            "audio_energy": round(features[5], 3),
            "audio_pitch": round(features[6], 3),
            "face_emotion": round(features[7], 3),
            "face_count_norm": round(features[8], 3),
            "hook_ratio": round(features[9], 3),
        },
        "recommendation": (
            "RENDER — konten ini berpotensi viral!"
            if result["ml_should_render"]
            else f"SKIP — skor {result['ml_viral_score']:.1f} < threshold {request.threshold}. "
            "Coba perbaiki judul dengan lebih banyak power words."
        ),
    }


@router.get("/providers", response_model=ProvidersOut)
async def list_providers(_current_user: User = Depends(get_current_active_user)):
    """Katalog provider dan model. Sumber tunggal untuk daftar di frontend."""
    providers = []
    for provider_id, models in MODEL_CATALOG.items():
        kind = PROVIDER_KIND.get(provider_id, "llm")
        providers.append(
            {
                "id": provider_id,
                "kind": kind,
                "free": bool(FREE_MODELS.get(provider_id)),
                "models": models,
                **provider_metadata(provider_id),
            }
        )
    return {
        "status": "success",
        "providers": providers,
        "tts": list(TTS_PROVIDERS),
        "stt": list(STT_PROVIDERS),
    }


@router.get("/platforms", response_model=PlatformsOut)
async def list_platforms(_current_user: User = Depends(get_current_active_user)):
    """Daftar platform shorts. Sumber tunggal untuk pilihan di frontend."""
    return {
        "status": "success",
        "platforms": [platform.value for platform in Platform],
        "default": Platform.shorts.value,
    }


class CalibrationBucket(BaseModel):
    bucket: str
    count: int
    mean_actual: float | None = None


class CalibrationReport(BaseModel):
    status: str
    samples: int
    correlation: float | None = None
    mean_predicted: float | None = None
    mean_actual: float | None = None
    buckets: list[CalibrationBucket] = []
    note: str = ""


@router.get("/calibration", response_model=CalibrationReport)
async def calibration_report_endpoint(
    limit: int = Query(500, ge=1, le=2000),
    _user: User = Depends(get_current_active_user),
):
    """Korelasi skor viral vs feedback nyata (analitik, bukan training)."""
    from backend.services.viral_predictor import calibration_report

    return await asyncio.to_thread(calibration_report, limit=limit)


@router.get("/model-status", response_model=ModelStatusOut)
async def model_status(_current_user: User = Depends(require_owner)):
    """Status scoring viral: rule-based, tanpa model/training."""
    return {
        "status": "success",
        "model": {
            "trained": False,
            "enabled": False,
            "confidence_mode": "rule_based",
        },
        "message": "Scoring viral sepenuhnya rule-based. Tidak ada model atau training data.",
    }


@router.post("/feedback", response_model=FeedbackOut)
async def record_feedback(
    request: PerformanceFeedback,
    _current_user: User = Depends(get_current_active_user),
):
    """
    Catat performa nyata klip setelah dipublish (untuk analitik, bukan training).
    """
    from backend.services.viral_predictor import record_actual_performance

    await asyncio.to_thread(
        record_actual_performance,
        clip_id=request.clip_id,
        actual_views=request.actual_views,
        actual_likes=request.actual_likes,
        actual_shares=request.actual_shares,
    )

    return {
        "status": "success",
        "clip_id": request.clip_id,
        "message": f"Performa klip {request.clip_id} tercatat untuk analitik.",
    }
