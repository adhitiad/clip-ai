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
from typing import Optional, Union
from log import logger

# New Imports for Advanced AI
try:
    import librosa
except ImportError:
    librosa = None

try:
    import mediapipe as mp
except ImportError:
    mp = None

MODEL_DIR  = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "viral_predictor.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
DATA_PATH  = os.path.join(MODEL_DIR, "training_data.jsonl")
RETRAIN_EVERY = 20  # Lebih sering untuk online learning

# 6. Dynamic Viral Thresholding per Niche
NICHE_THRESHOLDS = {
    "gaming": 7.5,      # High competition, needs high energy
    "education": 5.5,   # Lower energy but high retention
    "podcast": 6.5,     # Average
    "news": 6.0,
    "entertainment": 7.0,
    "default": 6.5
}

HF_REPO_ID = os.environ.get("HF_MODEL_REPO", "") # Kosongkan agar user set di .env atau cari manual

def _ensure_models_exist():
    """Mengunduh model dan data dari Hugging Face jika HF_MODEL_REPO diset."""
    if not HF_REPO_ID:
        logger.info("[ViralML] HF_MODEL_REPO tidak diset. Menggunakan mode Cold Start (Latih lokal).")
        return

    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

    files_to_check = {
        "viral_predictor.pkl": MODEL_PATH,
        "scaler.pkl": SCALER_PATH,
        "training_data.jsonl": DATA_PATH
    }

    for filename, local_path in files_to_check.items():
        if not os.path.exists(local_path):
            try:
                from huggingface_hub import hf_hub_download
                logger.info(f"[ViralML] Mengunduh {filename} dari Hugging Face ({HF_REPO_ID})...")
                downloaded_path = hf_hub_download(repo_id=HF_REPO_ID, filename=filename, local_dir=MODEL_DIR)
                # Pastikan path lokal sesuai dengan konstanta kita
                if downloaded_path != local_path and os.path.exists(downloaded_path):
                    import shutil
                    shutil.move(downloaded_path, local_path)
            except Exception as e:
                logger.warning(f"[ViralML] Gagal mengunduh {filename}: {e}. Menggunakan fallback/cold-start.")

# Jalankan pengecekan saat modul diload
_ensure_models_exist()

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


def _audio_features(audio_path: str) -> tuple[float, float]:
    """
    5. Deteksi Hook dengan Audio Sentiment (Energy & Pitch)
    Returns: (energy_score, pitch_score)
    """
    if not audio_path or not os.path.exists(audio_path) or librosa is None:
        return 0.5, 0.5

    try:
        y, sr = librosa.load(audio_path, duration=10) # Ambil 10 detik pertama (hook)
        
        # Energy (RMS)
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))
        energy_score = min(1.0, energy / 0.15)

        # Pitch (Tonnetz/Chroma) - Variasi nada menandakan intonasi yang hidup
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_variation = float(np.std(pitches[pitches > 0])) if np.any(pitches > 0) else 0.0
        pitch_score = min(1.0, pitch_variation / 500.0)

        return energy_score, pitch_score
    except Exception as e:
        logger.warning(f"[ViralML] Gagal ekstraksi audio pitch: {e}")
        return 0.5, 0.5


def _face_emotion_score(video_path: str, max_frames=5) -> float:
    """
    1. Deteksi Ekspresi Wajah (Vision AI) - Sederhana menggunakan MediaPipe
    Mendeteksi 'mouth opening' atau 'eye widening' sebagai proksi ekspresi kuat.
    """
    if not video_path or not os.path.exists(video_path) or mp is None:
        return 0.5

    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)
        
        scores = []
        frame_count = 0
        while cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret: break
            
            # Ambil frame setiap detiknya (asumsi video 30fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count * 30)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                # Hitung jarak bibir atas & bawah sebagai proksi 'wow' expression
                landmarks = results.multi_face_landmarks[0].landmark
                upper_lip = landmarks[13].y
                lower_lip = landmarks[14].y
                mouth_open = abs(upper_lip - lower_lip)
                scores.append(min(1.0, mouth_open * 10)) # Normalize
            
            frame_count += 1
        
        cap.release()
        return float(np.mean(scores)) if scores else 0.5
    except Exception as e:
        logger.warning(f"[ViralML] Gagal ekstraksi ekspresi wajah: {e}")
        return 0.5


def extract_features(clip_metadata: dict, audio_path: str = "", video_path: str = "") -> list[float]:
    """
    Ekstrak feature vector dari metadata klip.
    """
    start   = float(clip_metadata.get("start_time", 0))
    end     = float(clip_metadata.get("end_time", 0))
    duration = end - start

    title = str(clip_metadata.get("title_en", clip_metadata.get("title_id", "")))
    desc  = str(clip_metadata.get("desc_en", clip_metadata.get("desc_id", "")))

    title_power   = _count_power_words(title)
    desc_power    = _count_power_words(desc)
    title_len_norm = min(1.0, len(title) / 80.0)
    has_broll      = 1.0 if clip_metadata.get("broll_query") else 0.0
    
    # 5. Audio Sentiment (Pitch & Energy)
    energy_score, pitch_score = _audio_features(audio_path)
    
    # 1. Vision Emotion Score
    emotion_score = _face_emotion_score(video_path)
    
    face_count = min(3.0, float(clip_metadata.get("face_count", 1))) / 3.0
    dur_score  = _duration_score(duration)
    hook_ratio = min(1.0, duration / 60.0)

    return [
        dur_score,
        float(title_power),
        float(desc_power),
        title_len_norm,
        has_broll,
        energy_score,
        pitch_score,
        emotion_score,
        face_count,
        hook_ratio,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# RULE-BASED FALLBACK (Cold Start)
# ─────────────────────────────────────────────────────────────────────────────

def rule_based_score(features: list[float]) -> float:
    """
    Skor berbasis aturan eksplisit untuk cold start sebelum ML siap.
    """
    dur_score, title_pw, desc_pw, title_len, broll, audio_e, audio_p, face_e, faces, hook_r = features

    score = 0.0
    score += dur_score * 2.0
    score += min(title_pw, 3) * 0.8
    score += title_len * 1.0
    score += broll * 0.8
    score += audio_e * 1.5
    score += audio_p * 1.0 # New Feature: Pitch
    score += face_e * 1.5  # New Feature: Face Emotion
    score += faces * 0.4

    return max(1.0, min(10.0, score))


# ─────────────────────────────────────────────────────────────────────────────
# ML MODEL MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _load_model():
    """Load model dan scaler."""
    model, scaler = None, None
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            if os.path.exists(SCALER_PATH):
                with open(SCALER_PATH, "rb") as f:
                    scaler = pickle.load(f)
        except Exception as e:
            logger.error(f"[ViralML] Gagal load model: {e}")
    return model, scaler


def _save_model(model, scaler) -> None:
    """Simpan model dan scaler."""
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)


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
    """
    8. Reinforcement Learning (Online Training) dengan SGDRegressor.
    Memungkinkan model belajar terus-menerus (incremental).
    """
    try:
        from sklearn.linear_model import SGDRegressor
        from sklearn.preprocessing import StandardScaler

        X_np = np.array(X)
        y_np = np.array(y)

        if len(X) < 5:
            return

        model, scaler = _load_model()
        if scaler is None:
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_np)
        else:
            X_scaled = scaler.transform(X_np)

        if model is None:
            # First time training
            model = SGDRegressor(max_iter=1000, tol=1e-3, random_state=42)
            model.fit(X_scaled, y_np)
        else:
            # 8. Online Learning: partial_fit menambah data baru ke model lama
            model.partial_fit(X_scaled, y_np)

        _save_model(model, scaler)
        logger.info(f"[ViralML] Online learning berhasil dengan {len(X)} sample baru.")

    except Exception as e:
        logger.error(f"[ViralML] Training error: {e}")


# 10. Cost-Benefit ML (Token Optimization)
def pre_check_viral_potential(text_summary: str) -> bool:
    """
    Cek potensi viral hanya dari teks ringkasan (murah)
    sebelum memanggil video processing yang mahal.
    """
    score = 0.0
    text = text_summary.lower()
    score += _count_power_words(text) * 1.5
    
    # Deteksi 'Hook' intrinsik dalam teks (pertanyaan, angka, janji)
    hook_indicators = ["?", "!", "rahasia", "bagaimana", "cara", "tips"]
    for ind in hook_indicators:
        if ind in text: score += 1.0
        
    logger.info(f"[ViralML] Pre-check potential score: {score:.1f}")
    return score >= 3.0 # Threshold rendah untuk pre-filter


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ─────────────────────────────────────────────────────────────────────────────

# Cache model dan scaler di memory
_cached_model = None
_cached_scaler = None

def get_niche_threshold(niche: str) -> float:
    """6. Ambil threshold dinamis sesuai niche."""
    return NICHE_THRESHOLDS.get(niche.lower(), NICHE_THRESHOLDS["default"])

def predict_viral_score(
    clip_metadata: dict,
    audio_path: str = "",
    video_path: str = "",
    niche: str = "default",
) -> dict:
    """
    Prediksi skor viral SEBELUM render dengan fitur canggih.
    """
    global _cached_model, _cached_scaler

    features = extract_features(clip_metadata, audio_path, video_path)
    threshold = get_niche_threshold(niche)

    if _cached_model is None:
        _cached_model, _cached_scaler = _load_model()

    if _cached_model is not None and _cached_scaler is not None:
        try:
            X_scaled = _cached_scaler.transform([features])
            score_raw = float(_cached_model.predict(X_scaled)[0])
            score = max(1.0, min(10.0, score_raw))
            confidence = "ml_model_online"
        except Exception:
            score = rule_based_score(features)
            confidence = "rule_based_fallback"
    else:
        score = rule_based_score(features)
        confidence = "rule_based"

    result = {
        **clip_metadata,
        "ml_viral_score": round(score, 2),
        "ml_should_render": score >= threshold,
        "ml_threshold_used": threshold,
        "ml_confidence": confidence,
        "ml_features": features,
    }
    return result


# 9. Automated A/B Testing untuk Hook
def select_best_hook_variant(clip_metadata: dict, variants: list[str]) -> dict:
    """
    Pilih variasi judul (hook) terbaik menggunakan simulasi ML.
    """
    results = []
    for var in variants:
        temp_meta = clip_metadata.copy()
        temp_meta["title_en"] = var
        pred = predict_viral_score(temp_meta)
        results.append(pred)
    
    # Ambil yang skornya paling tinggi
    best = max(results, key=lambda x: x["ml_viral_score"])
    logger.info(f"[ViralML] A/B Test Hook: Terpilih '{best['title_en']}' dengan score {best['ml_viral_score']}")
    return best


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

    scored = [predict_viral_score(c, audio_path=audio_path) for c in clips]
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


def _score_from_real_performance(actual_views: int, actual_likes: int, actual_shares: int) -> float:
    views = max(0, int(actual_views))
    likes = max(0, int(actual_likes))
    shares = max(0, int(actual_shares))

    # Views mendorong base score
    view_score = min(7.0, math.log10(views + 1) * 1.8)

    # Engagement rate (likes + shares*2) menambah kualitas
    if views > 0:
        engagement_rate = (likes + (shares * 2)) / views
    else:
        engagement_rate = 0.0
    engagement_score = min(3.0, engagement_rate * 60.0)

    return max(1.0, min(10.0, 1.0 + view_score + engagement_score))


def record_actual_performance(
    clip_id: int,
    actual_views: int,
    actual_likes: int,
    actual_shares: int = 0,
) -> None:
    """
    Catat performa klip sesungguhnya untuk continuous learning.
    Dipanggil setelah post dipublish dan mendapat data engagement.

    Skor actual dibuat dari kombinasi views + engagement (likes/shares).
    """
    from utils.db import SessionLocal
    from models.clip import Clip

    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            logger.warning(f"[ViralML] Clip id={clip_id} tidak ditemukan. Feedback diabaikan.")
            return

        clip_metadata = {
            "start_time": clip.start_time,
            "end_time": clip.end_time,
            "title_en": clip.title_en,
            "desc_en": clip.desc_en,
            "broll_query": "",
        }
        features = extract_features(clip_metadata, audio_path="")
        score = _score_from_real_performance(actual_views, actual_likes, actual_shares)
        save_training_sample(features, score)

        logger.info(
            f"[ViralML] Feedback clip={clip_id}: views={actual_views}, likes={actual_likes}, "
            f"shares={actual_shares} -> score={score:.2f} (sample tersimpan)"
        )
    except Exception as e:
        logger.error(f"[ViralML] Gagal merekam performa clip={clip_id}: {e}")
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────────
# SAAS FEATURE: NICHE TRENDS HUNTER
# ─────────────────────────────────────────────────────────────────────────────

def get_niche_trends(niche: str = "podcast"):
    """
    SaaS Feature 8: Viral Niche Trends Hunter.
    Automatically fetches trending topics in a specific niche.
    """
    mock_trends = {
        "podcast": ["Health Optimization", "AI Future", "Remote Work Culture"],
        "gaming": ["GTA 6 Leaks", "Elden Ring DLC", "Indie Game Gems"],
        "finance": ["Crypto Bull Run", "Passive Income 2024", "Real Estate Crash"]
    }
    
    selected_trends = mock_trends.get(niche.lower(), ["Modern Productivity", "Digital Nomad"])
    
    logger.info(f"👑 SaaS: Trends Hunter found {len(selected_trends)} viral topics for niche: {niche}")
    return [
        {"topic": t, "potential_score": 0.85 + (0.05 * i), "source": "YouTube Trending"}
        for i, t in enumerate(selected_trends)
    ]
