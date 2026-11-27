"""
services/viral_predictor.py
============================
Viral Score Predictor berbasis aturan (tanpa model ML / tanpa training).

Skor 1-10 dihitung SEBELUM render dari sinyal:
  - Rasio durasi klip (30-60 det = ideal)
  - "Power words" pada judul/deskripsi
  - Panjang judul, B-Roll, energi & pitch audio
  - Emosi wajah, jumlah wajah, hook ratio

Tidak ada artefak ``.pkl``, training data, atau continuous learning model.
Feedback performa nyata tetap bisa dicatat untuk analitik (bukan training).
"""

import math
import os

import numpy as np
import pandas as pd

from backend.core.models import ViralFeatures, ViralScore
from backend.log import logger

try:
    import librosa
except ImportError:
    librosa = None

try:
    import mediapipe as mp
except ImportError:
    mp = None

# 6. Dynamic Viral Thresholding per Niche
NICHE_THRESHOLDS = {
    "gaming": 7.5,
    "education": 5.5,
    "podcast": 6.5,
    "news": 6.0,
    "entertainment": 7.0,
    "default": 6.5,
}

# ─────────────────────────────────────────────────────────────────────────────
# Power Words — kata yang terbukti meningkatkan CTR di TikTok/Shorts
# ─────────────────────────────────────────────────────────────────────────────
POWER_WORDS_ID = {
    "viral",
    "rahasia",
    "terbukti",
    "terungkap",
    "shocking",
    "mengejutkan",
    "luar biasa",
    "penting",
    "jangan lewatkan",
    "wajib tahu",
    "fakta",
    "trik",
    "cara",
    "tips",
    "rahasia dagang",
    "tercepat",
    "termurah",
    "terbaik",
    "eksklusif",
    "jarang diketahui",
}
POWER_WORDS_EN = {
    "viral",
    "secret",
    "shocking",
    "proven",
    "revealed",
    "crazy",
    "insane",
    "unbelievable",
    "must watch",
    "hack",
    "tips",
    "trick",
    "best",
    "top",
    "exclusive",
    "breaking",
    "ultimate",
    "crucial",
}


def _count_power_words(text: str) -> int:
    lowered = text.lower()
    return sum(1 for word in POWER_WORDS_ID | POWER_WORDS_EN if word in lowered)


def _duration_score(duration: float) -> float:
    """ideal 30-60 detik untuk short-form"""
    if duration <= 0:
        return 0.0
    if 20 <= duration <= 60:
        return 1.0
    if duration < 20:
        return max(0.0, duration / 20.0)
    return max(0.0, 1.0 - (duration - 60) / 90.0)


def _title_length_score(title: str) -> float:
    length = len(title.strip())
    if 25 <= length <= 70:
        return 1.0
    if length == 0:
        return 0.0
    return max(0.0, 1.0 - abs(length - 45) / 60.0)


def _audio_energy(audio_path: str) -> float:
    if not audio_path or not os.path.exists(audio_path) or librosa is None:
        return 0.5
    try:
        y, sr = librosa.load(audio_path, sr=None, mono=True, duration=10)
        rms = librosa.feature.rms(y=y)[0]
        return max(0.0, min(1.0, float(np.mean(rms)) * 8.0))
    except Exception:
        return 0.5


def _audio_pitch(audio_path: str) -> float:
    if not audio_path or not os.path.exists(audio_path) or librosa is None:
        return 0.5
    try:
        y, sr = librosa.load(audio_path, sr=None, mono=True, duration=10)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        valid = pitches[magnitudes > np.median(magnitudes)]
        if len(valid) == 0:
            return 0.5
        pitch = float(np.median(valid[valid > 0])) if np.any(valid > 0) else 0.0
        return max(0.0, min(1.0, pitch / 500.0))
    except Exception:
        return 0.5


def _face_features(video_path: str) -> tuple[float, float]:
    """Return (face_emotion_norm, face_count_norm) via MediaPipe, atau (0,0)."""
    if not video_path or not os.path.exists(video_path) or mp is None:
        return 0.0, 0.0
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, frame_count // 10)
        faces = []
        with mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        ) as detector:
            for frame_no in range(0, frame_count, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                ret, frame = cap.read()
                if not ret:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.process(rgb)
                faces.append(len(result.detections or []))
        cap.release()
        if not faces:
            return 0.0, 0.0
        avg = sum(faces) / len(faces)
        return min(1.0, avg / 2.0), min(1.0, avg / 3.0)
    except Exception:
        return 0.0, 0.0


def _hook_ratio(metadata: dict) -> float:
    text = " ".join(
        str(metadata.get(key, ""))
        for key in ("title_en", "title_id", "desc_en", "desc_id", "hook")
    )
    score = min(1.0, _count_power_words(text) / 3.0)
    if "?" in text or "!" in text:
        score = min(1.0, score + 0.2)
    return score


def extract_features(
    clip_metadata: dict, audio_path: str = "", video_path: str = ""
) -> list[float]:
    """
    Urutan fitur (POSITIONAL — jangan diubah tanpa update rule_based_score,
    tests, dan mapping /tools/viral-score):
      0 duration_score, 1 title_power_words, 2 desc_power_words,
      3 title_length_score, 4 has_broll, 5 audio_energy,
      6 audio_pitch, 7 face_emotion, 8 face_count_norm, 9 hook_ratio
    """
    start = float(clip_metadata.get("start_time", 0) or 0)
    end = float(clip_metadata.get("end_time", 0) or 0)
    duration = max(0.0, end - start)
    title = str(clip_metadata.get("title_en") or clip_metadata.get("title_id") or "")
    desc = str(clip_metadata.get("desc_en") or clip_metadata.get("desc_id") or "")
    face_emotion, face_count = _face_features(video_path)
    return [
        _duration_score(duration),
        float(min(3, _count_power_words(title))),
        float(min(3, _count_power_words(desc))),
        _title_length_score(title),
        1.0 if clip_metadata.get("broll_query") else 0.0,
        _audio_energy(audio_path),
        _audio_pitch(audio_path),
        face_emotion,
        face_count,
        _hook_ratio(clip_metadata),
    ]


# Bobot default mengikuti urutan positional ViralFeatures.
DEFAULT_SCORE_WEIGHTS = np.array([2.0, 0.8, 0.4, 1.0, 0.8, 1.5, 1.0, 1.5, 0.4, 1.2])
SCORE_WEIGHTS = DEFAULT_SCORE_WEIGHTS
WEIGHT_ENV = "VIRAL_SCORE_WEIGHTS"
WEIGHT_MIN, WEIGHT_MAX = 0.0, 3.0


def resolve_score_weights(env: dict | None = None) -> np.ndarray:
    """Bobot dari env `VIRAL_SCORE_WEIGHTS` (10 angka koma). Invalid → default."""
    source = env if env is not None else os.environ
    raw = str(source.get(WEIGHT_ENV, "")).strip()
    if not raw:
        return DEFAULT_SCORE_WEIGHTS.copy()
    try:
        values = [float(part.strip()) for part in raw.split(",")]
    except ValueError:
        logger.warning(f"[ViralScore] {WEIGHT_ENV} bukan angka; pakai default.")
        return DEFAULT_SCORE_WEIGHTS.copy()
    if len(values) != 10 or any(
        not WEIGHT_MIN <= value <= WEIGHT_MAX for value in values
    ):
        logger.warning(
            f"[ViralScore] {WEIGHT_ENV} harus 10 angka {WEIGHT_MIN}-{WEIGHT_MAX}; pakai default."
        )
        return DEFAULT_SCORE_WEIGHTS.copy()
    return np.asarray(values, dtype=float)


def rule_based_score(features: list[float] | ViralFeatures) -> float:
    """Skor 1-10 via dot-product numpy (satu-satunya mode scoring)."""
    vector = (
        features.as_array()
        if isinstance(features, ViralFeatures)
        else np.asarray(features, dtype=float)
    )
    if vector.shape != (10,):
        raise ValueError("Fitur viral harus tepat 10 nilai")
    # power words dibatasi maksimal 3 (indeks 1 & 2)
    vector = vector.copy()
    vector[1:3] = np.minimum(vector[1:3], 3.0)
    return float(np.clip(np.dot(vector, resolve_score_weights()), 1.0, 10.0))


def pre_check_viral_potential(text_summary: str) -> bool:
    """
    Pre-filter teks ringan sebelum pipeline video yang mahal.

    Hanya menolak bila transkrip benar-benar kosong. Teks apa pun yang
    tersedia (walau pendek) tetap diproses — jangan memblokir pipeline
    hanya karena tidak ada "power words".
    """
    text = text_summary.lower().strip()
    if not text:
        logger.warning("[ViralScore] Pre-check: transkrip kosong, lewati video.")
        return False
    score = _count_power_words(text) * 1.5
    for indicator in ["?", "!", "rahasia", "bagaimana", "cara", "tips"]:
        if indicator in text:
            score += 1.0
    logger.info(f"[ViralScore] Pre-check potential score: {score:.1f} (diterima)")
    return True


def get_niche_threshold(niche: str) -> float:
    """Ambil threshold dinamis sesuai niche."""
    return NICHE_THRESHOLDS.get(niche.lower(), NICHE_THRESHOLDS["default"])


def predict_viral_score(
    clip_metadata: dict,
    audio_path: str = "",
    video_path: str = "",
    niche: str = "default",
    threshold: float | None = None,
) -> dict:
    """
    Prediksi skor viral SEBELUM render (tanpa model, tanpa training).

    ``threshold`` menimpa threshold default per-niche bila diberikan.
    """
    feature_values = extract_features(clip_metadata, audio_path, video_path)
    features = ViralFeatures.from_list(feature_values)
    if threshold is None:
        threshold = get_niche_threshold(niche)
    score = rule_based_score(features)
    result = ViralScore(
        score=round(score, 2),
        threshold=threshold,
        should_render=score >= threshold,
        features=features,
    )

    return {
        **clip_metadata,
        "ml_viral_score": result.score,
        "ml_should_render": result.should_render,
        "ml_threshold_used": result.threshold,
        "ml_confidence": result.confidence,
        "ml_features": feature_values,
    }


def select_best_hook_variant(clip_metadata: dict, variants: list[str]) -> dict:
    """Pilih variasi judul (hook) dengan skor aturan tertinggi."""
    results = []
    for var in variants:
        temp_meta = clip_metadata.copy()
        temp_meta["title_en"] = var
        results.append(predict_viral_score(temp_meta))
    best = max(results, key=lambda x: x["ml_viral_score"])
    logger.info(
        f"[ViralScore] A/B Test Hook: '{best['title_en']}' score {best['ml_viral_score']}"
    )
    return best


def batch_predict_and_filter(
    clips: list[dict],
    audio_path: str = "",
    threshold: float = 6.5,
    always_keep_best: int = 1,
) -> list[dict]:
    """Skor & filter klip kandidat (rule-based), urut dari skor tertinggi."""
    if not clips:
        return []
    scored = [
        predict_viral_score(c, audio_path=audio_path, threshold=threshold)
        for c in clips
    ]
    frame = pd.DataFrame(scored).sort_values("ml_viral_score", ascending=False)
    keep = frame[frame["ml_should_render"]]
    if len(keep) < always_keep_best:
        keep = frame.head(always_keep_best)
    should_render = keep.to_dict("records")
    skipped = len(clips) - len(should_render)
    logger.info(
        f"[ViralScore] {len(should_render)}/{len(clips)} klip lolos ({skipped} diskip)"
    )
    return should_render


def _score_from_real_performance(
    actual_views: int, actual_likes: int, actual_shares: int
) -> float:
    views = max(0, int(actual_views))
    likes = max(0, int(actual_likes))
    shares = max(0, int(actual_shares))

    view_score = min(7.0, math.log10(views + 1) * 1.8)
    engagement_rate = ((likes + shares * 2) / views) if views > 0 else 0.0
    engagement_score = min(3.0, engagement_rate * 60.0)

    return max(1.0, min(10.0, 1.0 + view_score + engagement_score))


def record_actual_performance(
    clip_id: int,
    actual_views: int,
    actual_likes: int,
    actual_shares: int = 0,
) -> None:
    """Catat performa nyata ke log untuk analitik (bukan training model)."""
    from backend.models.clip import Clip
    from backend.models.feedback import PerformanceFeedbackRecord
    from backend.utils.db import SessionLocal

    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            logger.warning(f"[ViralScore] Clip id={clip_id} tidak ditemukan.")
            return
        score = _score_from_real_performance(actual_views, actual_likes, actual_shares)
        db.add(
            PerformanceFeedbackRecord(
                clip_id=clip_id,
                actual_views=actual_views,
                actual_likes=actual_likes,
                actual_shares=actual_shares,
                predicted_score=float(clip.score or 0.0),
                real_score=score,
            )
        )
        db.commit()
        logger.info(
            f"[ViralScore] Feedback clip={clip_id}: views={actual_views}, "
            f"likes={actual_likes}, shares={actual_shares} -> score={score:.2f}"
        )
    except Exception as exc:
        logger.error(f"[ViralScore] Gagal mencatat feedback clip={clip_id}: {exc}")
    finally:
        db.close()


def calibration_report(limit: int = 500, db=None) -> dict:
    """Korelasi skor prediksi vs performa nyata (pandas, tanpa training)."""
    from backend.models.feedback import PerformanceFeedbackRecord
    from backend.utils.db import SessionLocal

    owns_db = db is None
    session = db or SessionLocal()
    try:
        rows = (
            session.query(PerformanceFeedbackRecord)
            .order_by(PerformanceFeedbackRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        frame = pd.DataFrame(
            [
                {
                    "predicted_score": float(row.predicted_score),
                    "real_score": float(row.real_score),
                }
                for row in rows
            ]
        )
    finally:
        if owns_db:
            session.close()

    samples = int(len(frame))
    if samples < 2:
        return {
            "status": "success",
            "samples": samples,
            "correlation": None,
            "mean_predicted": None,
            "mean_actual": None,
            "buckets": [],
            "note": "Minimal 2 feedback diperlukan untuk korelasi.",
        }

    correlation = float(frame["predicted_score"].corr(frame["real_score"]))
    if pd.isna(correlation):
        correlation = 0.0
    cuts = pd.cut(
        frame["predicted_score"], bins=[0, 4, 7, 10], labels=["1-4", "5-7", "8-10"]
    )
    grouped = frame.groupby(cuts, observed=False)["real_score"].agg(["count", "mean"])
    buckets = [
        {
            "bucket": str(label),
            "count": int(row["count"]),
            "mean_actual": round(float(row["mean"]), 2)
            if pd.notna(row["mean"])
            else None,
        }
        for label, row in grouped.iterrows()
    ]
    return {
        "status": "success",
        "samples": samples,
        "correlation": round(correlation, 3),
        "mean_predicted": round(float(frame["predicted_score"].mean()), 2),
        "mean_actual": round(float(frame["real_score"].mean()), 2),
        "buckets": buckets,
        "note": "Analitik rule-based; tidak ada model/training. Bobot diubah via VIRAL_SCORE_WEIGHTS.",
    }
