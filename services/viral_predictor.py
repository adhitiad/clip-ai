"""
services/viral_predictor.py
=============================
Viral Score Predictor menggunakan ML (scikit-learn)

Model memprediksi skor viral 1-10 SEBELUM render, berdasarkan sinyal:
  - Panjang hook (detik)
  - Jumlah kata "power words" pada judul
  - Energi audio rata-rata (RMS dari numpy)
  - Jumlah wajah terdeteksi
  - Rasio durasi klip (30-60 det = ideal)
  - Adanya B-Roll query
  - Panjang karakter judul

Model:
  - GradientBoostingRegressor (akurat, ringan)
  - Auto-train jika belum ada model tersimpan
  - Retrain otomatis setiap 100 klip baru (continuous learning)
  - Simpan model ke: models/viral_predictor.pkl

Jika model belum dilatih (cold start):
  - Gunakan rule-based scoring sebagai fallback
  - Setiap klip yang dirender memperkaya training data
"""

import os
import json
import math
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional
from log import logger

MODEL_DIR  = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "viral_predictor.pkl")
DATA_PATH  = os.path.join(MODEL_DIR, "training_data.jsonl")
RETRAIN_EVERY = 50  # Retrain setelah N sample baru

os.makedirs(MODEL_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Power Words — kata yang terbukti meningkatkan CTR di TikTok/Shorts
# ─────────────────────────────────────────────────────────────────────────────
POWER_WORDS_ID = {
    "viral", "rahasia", "terbukti", "terungkap", "shocking", "mengejutkan",
    "wajib", "tonton", "jangan", "ternyata", "sebenarnya", "fakta",
    "nyata", "gila", "keren", "amazing", "terbaik", "wow", "pov",
    "jujur", "berani", "kontroversial", "banned", "dilarang", "tersembunyi",
    "bocoran", "eksklusif", "pertama", "terbaru", "trending", "hot",
}

POWER_WORDS_EN = {
    "secret", "revealed", "shocking", "viral", "hidden", "banned", "truth",
    "exposed", "pov", "honest", "crazy", "insane", "must", "watch",
    "exclusive", "breaking", "never", "first", "top", "best", "worst",
    "real", "uncut", "raw", "controversial", "leaked",
}


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _count_power_words(text: str) -> int:
    """Hitung jumlah power words dalam teks."""
    words = set(text.lower().split())
    return len(words & (POWER_WORDS_ID | POWER_WORDS_EN))


def _duration_score(seconds: float) -> float:
    """
    Skor durasi: optimal 45-60 detik = 1.0, terlalu pendek/panjang berkurang.
    """
    if seconds <= 0:
        return 0.0
    # Bell curve centered at 50s, lebar 40s
    return math.exp(-0.5 * ((seconds - 50) / 25) ** 2)


def _audio_energy(audio_path: str) -> float:
    """
    Hitung energi audio rata-rata (RMS) dari file audio.
    Return 0.0 jika file tidak ada atau error.
    Range: 0.0 - 1.0 (normalized)
    """
    if not audio_path or not os.path.exists(audio_path):
        return 0.5  # Default neutral

    try:
        # Gunakan ffmpeg untuk extract samples ke raw PCM
        import subprocess
        result = subprocess.run(
            [
                "ffmpeg", "-i", audio_path,
                "-f", "f32le",          # 32-bit float PCM
                "-acodec", "pcm_f32le",
                "-ar", "8000",          # Downsample ke 8kHz untuk kecepatan
                "-ac", "1",             # Mono
                "-t", "30",             # Maksimal 30 detik pertama
                "pipe:1"
            ],
            capture_output=True,
            timeout=15
        )
        if result.returncode != 0 or not result.stdout:
            return 0.5

        samples = np.frombuffer(result.stdout, dtype=np.float32)
        if len(samples) == 0:
            return 0.5

        rms = float(np.sqrt(np.mean(samples ** 2)))
        # Normalize ke 0-1 (nilai RMS audio normal sekitar 0.05-0.3)
        normalized = min(1.0, rms / 0.25)
        return normalized

    except Exception:
        return 0.5


def extract_features(clip_metadata: dict, audio_path: str = "") -> list[float]:
    """
    Ekstrak feature vector dari metadata klip untuk prediksi ML.

    Features:
      [0] duration_score        — skor durasi (0-1)
      [1] title_power_words     — jumlah power words di judul
      [2] desc_power_words      — jumlah power words di deskripsi
      [3] title_length_norm     — panjang judul ternormalisasi (0-1)
      [4] has_broll             — ada B-Roll query (0/1)
      [5] audio_energy          — energi audio RMS (0-1)
      [6] face_count            — estimasi jumlah wajah (0-3+, diclip)
      [7] hook_ratio            — rasio durasi terhadap panjang ideal (0-1)
    """
    start   = float(clip_metadata.get("start_time", 0))
    end     = float(clip_metadata.get("end_time", 0))
    duration = end - start

    title = str(clip_metadata.get("title_en", clip_metadata.get("title_id", "")))
    desc  = str(clip_metadata.get("desc_en", clip_metadata.get("desc_id", "")))

    title_power   = _count_power_words(title)
    desc_power    = _count_power_words(desc)
    title_len_norm = min(1.0, len(title) / 80.0)   # 80 karakter = ideal
    has_broll      = 1.0 if clip_metadata.get("broll_query") else 0.0
    audio_energy   = _audio_energy(audio_path)
    face_count     = min(3.0, float(clip_metadata.get("face_count", 1))) / 3.0
    dur_score      = _duration_score(duration)
    hook_ratio     = min(1.0, duration / 60.0)

    return [
        dur_score,
        float(title_power),
        float(desc_power),
        title_len_norm,
        has_broll,
        audio_energy,
        face_count,
        hook_ratio,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# RULE-BASED FALLBACK (Cold Start)
# ─────────────────────────────────────────────────────────────────────────────

def rule_based_score(features: list[float]) -> float:
    """
    Skor berbasis aturan eksplisit untuk cold start sebelum ML siap.
    Return score 1-10.
    """
    dur_score, title_pw, desc_pw, title_len, has_broll, audio_e, faces, hook_r = features

    score = 0.0
    score += dur_score * 2.5          # durasi ideal → max 2.5 poin
    score += min(title_pw, 3) * 0.8  # power words judul → max 2.4 poin
    score += min(desc_pw, 2) * 0.4   # power words deskripsi → max 0.8 poin
    score += title_len * 1.0          # judul yang baik → max 1.0 poin
    score += has_broll * 0.8          # ada b-roll → +0.8
    score += audio_e * 1.5            # energi tinggi → max 1.5 poin
    score += faces * 0.5              # wajah terdeteksi → max 0.5 poin

    # Clamp ke 1-10
    return max(1.0, min(10.0, score))


# ─────────────────────────────────────────────────────────────────────────────
# ML MODEL MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _load_model():
    """Load model dari disk jika ada."""
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"[ViralML] Gagal load model: {e}")
    return None


def _save_model(model) -> None:
    """Simpan model ke disk."""
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model)


def _load_training_data() -> tuple[list, list]:
    """Load semua training data dari JSONL file."""
    X, y = [], []
    if not os.path.exists(DATA_PATH):
        return X, y
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                X.append(obj["features"])
                y.append(obj["viral_score"])
            except (json.JSONDecodeError, KeyError):
                continue
    return X, y


def save_training_sample(features: list[float], viral_score: float) -> None:
    """
    Simpan satu sample ke training data.
    Dipanggil setelah user memberikan feedback (thumbs up/down)
    atau setelah rendering klip berhasil.
    """
    sample = {"features": features, "viral_score": float(viral_score)}
    with open(DATA_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(sample) + "\n")

    # Check apakah perlu retrain
    X, y = _load_training_data()
    if len(X) >= RETRAIN_EVERY and len(X) % RETRAIN_EVERY == 0:
        logger.info(f"[ViralML] {len(X)} samples tersedia, melakukan retrain...")
        train_model(X, y)


def train_model(X: list, y: list) -> None:
    """Train atau retrain model GBR dengan data yang ada."""
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import cross_val_score

        if len(X) < 10:
            logger.warning(f"[ViralML] Data terlalu sedikit ({len(X)} samples) untuk training.")
            return

        logger.info(f"[ViralML] Training model dengan {len(X)} samples...")
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("gbr", GradientBoostingRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            ))
        ])
        model.fit(X, y)

        # Cross-validation score
        if len(X) >= 20:
            scores = cross_val_score(model, X, y, cv=3, scoring="r2")
            logger.info(f"[ViralML] Model R2 score (CV): {scores.mean():.3f} +/- {scores.std():.3f}")

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"[ViralML] Model disimpan ke {MODEL_PATH}")

    except ImportError:
        logger.error("[ViralML] scikit-learn belum terinstall. Jalankan: pip install scikit-learn")
    except Exception as e:
        logger.error(f"[ViralML] Training error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ─────────────────────────────────────────────────────────────────────────────

# Cache model di memory
_cached_model = None

def predict_viral_score(
    clip_metadata: dict,
    audio_path: str = "",
    threshold: float = 6.5,
) -> dict:
    """
    Prediksi skor viral SEBELUM render.

    Returns dict dengan keys tambahan:
      - "ml_viral_score": float (1-10)
      - "ml_should_render": bool (True jika score >= threshold)
      - "ml_confidence": "ml_model" atau "rule_based"
      - "ml_features": list (untuk debugging)
    """
    global _cached_model

    features = extract_features(clip_metadata, audio_path)

    # Coba load model (dengan cache)
    if _cached_model is None:
        _cached_model = _load_model()

    if _cached_model is not None:
        try:
            score_raw = float(_cached_model.predict([features])[0])
            score = max(1.0, min(10.0, score_raw))
            confidence = "ml_model"
        except Exception as e:
            logger.error(f"[ViralML] Prediksi ML error, fallback rule-based: {e}")
            score = rule_based_score(features)
            confidence = "rule_based_fallback"
    else:
        score = rule_based_score(features)
        confidence = "rule_based"

    result = {
        **clip_metadata,
        "ml_viral_score": round(score, 2),
        "ml_should_render": score >= threshold,
        "ml_confidence": confidence,
        "ml_features": features,
    }

    logger.info(
        f"[ViralML] '{clip_metadata.get('title_id', 'Untitled')[:40]}' "
        f"→ Score: {score:.1f}/10 "
        f"({'RENDER' if result['ml_should_render'] else 'SKIP'}) "
        f"[{confidence}]"
    )
    return result


def batch_predict_and_filter(
    clips: list[dict],
    audio_path: str = "",
    threshold: float = 6.5,
    always_keep_best: int = 1,
) -> list[dict]:
    """
    Prediksi semua klip, filter yang layak render.

    Args:
        clips: List clip metadata dari AI pipeline
        audio_path: Path audio untuk ekstraksi energi
        threshold: Minimal skor untuk dirender
        always_keep_best: Selalu keep N klip terbaik meskipun di bawah threshold
                          (mencegah tidak ada yang dirender sama sekali)

    Returns:
        List klip yang lolos filter, urut dari skor tertinggi
    """
    if not clips:
        return []

    logger.info(f"\n[ViralML] Mengevaluasi {len(clips)} klip kandidat...")

    scored = [predict_viral_score(c, audio_path, threshold) for c in clips]
    scored.sort(key=lambda x: x["ml_viral_score"], reverse=True)

    should_render = [c for c in scored if c["ml_should_render"]]

    # Pastikan minimal N klip terbaik tetap dirender
    if len(should_render) < always_keep_best:
        should_render = scored[:always_keep_best]

    skipped = len(clips) - len(should_render)
    logger.info(
        f"[ViralML] Hasil filter: {len(should_render)}/{len(clips)} klip akan dirender "
        f"({skipped} diskip, hemat {skipped * 100 // len(clips) if clips else 0}% resource)"
    )
    return should_render


def record_actual_performance(clip_id: int, actual_views: int, actual_likes: int) -> None:
    """
    Catat performa klip sesungguhnya untuk continuous learning.
    Dipanggil setelah post dipublish dan mendapat data engagement.

    Skor actual = log10(views) normalized ke 1-10
    """
    # Normalize views ke 1-10 (viral >100k views = ~10)
    if actual_views > 0:
        score = min(10.0, math.log10(actual_views + 1) * 2.0)
    else:
        score = 1.0

    # Load features klip dari DB (simplified: pakai clip_id sebagai identifier)
    # Dalam implementasi penuh, load dari DB berdasarkan clip_id
    # Di sini kita simpan placeholder untuk di-match nanti
    logger.info(f"[ViralML] Performa klip {clip_id}: {actual_views} views → skor {score:.1f}")
    # TODO: integrasi dengan DB untuk load features lalu save_training_sample(features, score)
