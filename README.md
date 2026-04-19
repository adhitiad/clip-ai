# 🎬 Ultimate AI Clipper SaaS
**Autonomous Content Factory - Dari Tren Google ke Klip Viral secara Otomatis.**

Ultimate AI Clipper adalah platform SaaS Backend berbasis AI yang dirancang untuk memangkas waktu kerja editor video dari jam-jaman menjadi hitungan detik. Sistem ini mencari tren sendiri, menganalisis niche, mencari video sumber, dan memproduksi 3 varian klip viral sekaligus lengkap dengan subtitle, B-Roll, dan dubbing AI.

---

## 🔥 Fitur Utama (State-of-the-Art)

### 🎯 1. Niche Discovery & AI Analysis
- **Google Trends RSS Engine**: Mengambil topik paling trending secara real-time tanpa perlu API Key berbayar.
- **AI Niche Strategist**: Menggunakan **LLaMA 3 (via Groq)** untuk membedah tren menjadi ide konten, hook, dan query pencarian YouTube yang spesifik.

### 🤖 2. Autonomous Content Sourcing
- **YouTube Intelligence**: Mencari video sumber berkualitas tinggi secara otomatis menggunakan metadata dan RSS kanal-kanal besar.
- **Auto-Queue Pipeline**: Sekali klik, sistem akan mengantrekan proses dari pencarian hingga rendering secara otonom.

### 🎭 3. Multi-Cam & AI Layout
- **Active Speaker Tracking**: Menggunakan **MediaPipe** untuk mendeteksi wajah dan mengatur layout (Crop 9:16, Split Screen/Podcast Mode).
- **Retention Hacks**: Integrasi otomatis B-Roll (GTA/Minecraft gameplay) untuk menjaga retensi penonton di TikTok/Shorts.

### 🏆 4. Viral Score Predictor (ML)
- **Pre-Render Evaluation**: Model ML (scikit-learn) memperkirakan probabilitas viral klip (1-10) sebelum CPU membuang daya untuk rendering.
- **Continuous Learning**: Sistem belajar dari data views dan likes nyata untuk meningkatkan akurasi prediksi.

### 🗣️ 5. AI Voice-Over Auto Dubbing
- **ElevenLabs Integration**: Dubbing suara manusia yang sangat realistis.
- **Multilingual Support**: Mendukung ganti bahasa otomatis (Dubbing Inggris ke Indonesia atau sebaliknya).
- **Auto-Sync**: Kecepat bicara AI disesuaikan secara otomatis dengan durasi klip video.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.13+)
- **AI/LLM**: Groq (LLaMA 3), Hugging Face (Translation)
- **Computer Vision**: MediaPipe, OpenCV
- **Audio/Video**: FFmpeg, Groq Whisper (Transkripsi)
- **Database**: PostgreSQL (SQLAlchemy), Redis (Celery Broker)
- **ML**: Scikit-learn, Numpy
- **Distribution**: Docker & Docker Compose

---

## 🚀 Memulai (Setup Cepat)

### 1. Prasyarat
- Python 3.11+
- FFmpeg terinstall di sistem
- Redis server (untuk Celery)

### 2. Instalasi
```bash
# Clone repository
git clone https://github.com/username/clip-ai.git
cd clip-ai

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # atau venv\Scripts\activate di Windows

# Install dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi Environment
Buat file `.env` di root direktori:
```env
GROQ_API_KEY=gsk_your_key_here
ELEVENLABS_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@localhost/db_name
PORT=8000
```

### 4. Jalankan Aplikasi
```bash
# Terminal 1: Jalankan API Server
python main.py

# Terminal 2: Jalankan Celery Worker (untuk rendering)
celery -A worker worker --loglevel=info -P solo
```

---

## 🛣️ API Endpoints Mapping

| Fitur | Endpoint |
|--- |--- |
| **Niche Discovery** | `GET /niche/suggest` |
| **Video Search** | `GET /niche/find-videos` |
| **Auto Pipeline** | `POST /niche/analyze-and-queue` |
| **AI Dubbing** | `POST /tools/dub` |
| **Viral Prediction** | `POST /tools/viral-score` |

---

## 📈 Roadmap Pengembangan
- [x] Integrasi Google Trends RSS
- [x] Viral Score Predictor ML
- [x] Auto Dubbing (ElevenLabs)
- [ ] Auto-Publisher ke TikTok/YouTube API
- [ ] Next.js Modern Dashboard
- [ ] Stripe/Midtrans Credit System

---

## 🛡️ Lisensi
Ultimate AI Clipper adalah software komersial. Seluruh hak cipta dilindungi.

---
*Dibuat dengan ❤️ oleh Antigravity AI Team.*
