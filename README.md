# 🎬 Ultimate AI Clipper SaaS
**Autonomous Content Factory - Dari Tren Google ke Klip Viral secara Otomatis.**

Ultimate AI Clipper adalah platform SaaS Backend berbasis AI yang dirancang untuk memangkas waktu kerja editor video dari jam-jaman menjadi hitungan detik. Sistem ini mencari tren sendiri, menganalisis niche, mencari video sumber, dan memproduksi 3 varian klip viral sekaligus lengkap dengan subtitle, B-Roll, dan dubbing AI.

---

## 🔥 Fitur Utama (State-of-the-Art)

### 🎯 1. Niche Discovery & AI Analysis
- **Google Trends RSS Engine**: Mengambil topik paling trending secara real-time tanpa perlu API Key berbayar.
- **AI Niche Strategist**: Menggunakan **LLaMA 3 (via Groq)** untuk membedah tren menjadi ide konten, hook, dan query pencarian YouTube yang spesifik.
- **Exa Web Search**: Cari berita dan artikel web terbaru beserta highlights untuk riset konten yang lebih tajam.

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
- **Web Search**: Exa (`exa-py`)
- **Computer Vision**: MediaPipe, OpenCV
- **Audio/Video**: FFmpeg, Groq Whisper (Transkripsi)
- **Database**: PostgreSQL (SQLAlchemy), Redis (Celery Broker)
- **ML**: Scikit-learn, Numpy
- **Distribution**: Docker & Docker Compose

---

## 🚀 Memulai (Setup Cepat)

### 1. Prasyarat Sistem (Penting untuk Windows)

- **Python 3.11+**
- **FFmpeg & FFprobe**: 
    1. Download binary FFmpeg untuk Windows dari [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
    2. Ekstrak dan tambahkan folder `bin` (yang berisi `ffmpeg.exe` dan `ffprobe.exe`) ke **Environment Variables (PATH)** sistem Anda.
    3. Verifikasi dengan perintah `ffmpeg -version` di Command Prompt.
- **PostgreSQL Server**:
    1. Instal [PostgreSQL](https://www.postgresql.org/download/windows/).
    2. Pastikan service berjalan.
    3. Buat database secara manual:
       ```sql
       CREATE DATABASE clipper_db;
       ```
- **Redis Server**: Diperlukan sebagai message broker untuk Celery. Bisa dijalankan via Docker atau WSL.

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
EXA_API_KEY=exa_your_key_here
ELEVENLABS_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/clipper_db
PEXELS_API_KEY=your_pexels_key
PORT=8000
```

> [!CAUTION]
> **Pexels API Key** diperlukan agar fitur B-Roll (footage Minecraft/GTA) dapat diunduh. Tanpa ini, video rintisan akan gagal diproduksi.

### 4. Jalankan Aplikasi
```bash
# Terminal 1: Jalankan API Server
python main.py

# Terminal 2: Jalankan Celery Worker (untuk rendering)
celery -A worker:celery_app worker --loglevel=info -P solo
```

> [!NOTE]
> Di Windows, Celery harus dijalankan dengan argumen `-P solo`. Argumen ini memastikan kestabilan proses rendering di Windows, namun berarti worker hanya akan memproses **satu tugas rendering** secara sekuensial (satu per satu).

---

## 🛣️ API Endpoints Mapping

| Fitur | Endpoint |
|--- |--- |
| **Niche Discovery** | `GET /niche/suggest` |
| **Video Search** | `GET /niche/find-videos` |
| **Web Search (Exa)** | `GET /niche/search-web` |
| **Auto Pipeline** | `POST /niche/analyze-and-queue` |
| **AI Dubbing** | `POST /tools/dub` |
| **Viral Prediction** | `POST /tools/viral-score` |
| **Dashboard (Role-based)** | `GET /dashboard/overview` |
| **User Growth (Admin Ops)** | `GET /dashboard/user-growth` |
| **History (Role-based)** | `GET /dashboard/history` |
| **User Profile (Self)** | `GET /dashboard/profile` |
| **User Settings (Self)** | `PATCH /dashboard/profile-settings` |
| **User Profile by ID (Owner/Staff)** | `GET /dashboard/users/{user_id}/profile` |
| **Owner Profile Settings** | `GET/PATCH /dashboard/owner/profile-settings` |
| **Owner Monitor** | `GET /dashboard/owner/monitor` |

---

## 📈 Roadmap Pengembangan
- [x] Integrasi Google Trends RSS
- [x] Viral Score Predictor ML
- [x] Auto Dubbing (ElevenLabs)
- [x] Backend Dashboard API (Role-based OWNER/STAFF/USER)
- [ ] Auto-Publisher ke TikTok/YouTube API
- [ ] Next.js Modern Dashboard
- [ ] Stripe/Midtrans Credit System

---

## 🛡️ Lisensi
Ultimate AI Clipper adalah software komersial. Seluruh hak cipta dilindungi.

---
*Dibuat dengan ❤️ oleh Antigravity AI Team.*
