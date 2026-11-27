# Goal & Workflow — Agent Shorts/Reels/TikTok

Dokumen ini menjawab: **apa tujuannya**, **apa alurnya**, dan **bagaimana cara menjalankannya**.
Untuk kontrak endpoint lihat [`API.md`](API.md); untuk aturan agent lihat [`AGENTS.md`](../AGENTS.md) dan `.agents/rules/*.md`.
Untuk daftar pekerjaan yang tersisa lihat [`TASKS.md`](TASKS.md).

---

## 1. Goal (Tujuan)

Membangun **agent konten short-form** (TikTok / Reels / YouTube Shorts) yang menghasilkan video yang bagus, dengan batasan tegas:

| Goal | Penjelasan |
| --- | --- |
| Hasil konten bagus | Hook kuat di 1,5 detik pertama, judul overlay ≤8 kata, caption dinamis, hashtag relevan, format vertikal 9:16 |
| Tanpa model ML | Tidak ada `.pkl`, training data, `train_model`, atau endpoint retrain. Scoring viral **rule-based** saja |
| Multi-provider LLM | LangChain `init_chat_model` + autodetect `langchain_*` + katalog provider; pilih lewat **select**, fallback **input manual** |
| Env terpusat | Semua konfigurasi lewat `backend/core/env.py` → `.env` (process env menang) |
| UUID v7 | Semua ID/referral baru pakai `uuid.uuid7()` (stdlib Python 3.14) |
| Test wajib | Setiap fitur backend harus punya test di `tests/**`; gate `scripts/gate.py` harus hijau |
| Dagangan tetap jalan | Pipeline render existing (FFmpeg + MoviePy + Taskiq) dipakai, bukan ditulis ulang |

### Definition of Done

- `uv run python scripts/gate.py` → **Gate passed** (ruff check, ruff format, `docs/openapi sync`, compileall, PostgreSQL ping, pytest, import app/worker).
- `POST /agent/shorts` dengan `render_video=false` mengembalikan `brief` JSON.
- `POST /agent/shorts` dengan `render_video=true` + `video_url` mengantre ke `shorts-render` (RabbitMQ primer, Taskiq fallback) dan file MP4 9:16 muncul di `output/`.
- Tidak ada file `.pkl` / `training_data.jsonl` / jalur training di repo (`tests/test_no_model.py` menjaganya).

---

> **Login Google-only**: `POST /auth/google` memverifikasi Google ID token (`GOOGLE_CLIENT_ID`)
> lalu mengeluarkan Bearer JWT. Tidak ada `/auth/token`, `/auth/register`, atau password.

## 2. Workflow (Alur)

### 2.1 Alur utama (end-to-end)

```text
[.env / env.py]
      │  load_env("backend")  →  SECRET_KEY, DATABASE_URL, API keys, AGENT_PROVIDER/MODEL
      ▼
[Client] ──POST /auth/google──▶ [JWT Bearer]
      │
      ▼
POST /agent/shorts
      │
      ├─1. Bearer JWT terverifikasi   → 401 token invalid, 403 email di luar whitelist
      ├─2. _few_shot(topic)           → Pinecone/DB; fallback aman jika gagal
      ├─3. plan_shorts()              → agent_llm (LangChain) + structured output ShortsPlan
      │       └─ provider: argumen → AGENT_PROVIDER/AGENT_MODEL → discovery langchain_*
      │          (interaktif: select nomor; jika tidak ada → input "provider/model")
      ├─4. render_video=false?        → BALAS {status:"brief", brief: ShortsPlan}  [SELESAI]
      │
      └─5. render_video=true:
             ├─ video_url wajib (422 jika kosong) atau auto_discover=true + topic → AI cari 2–10 video (>4 menit) dari YouTube/Exa/Tavily/Firecrawl/Selenium ke `download/`
             ├─ transcript YouTube VTT / audio → process_video_ai_logic() → timing klip asli
             ├─ _apply_plan_to_clips() → hook/judul/caption/hashtag agent digabung ke timing asli
             ├─ antrean `shorts-render` via RabbitMQ (primary) / Taskiq fallback
             └─ BALAS {status:"processing", task_id, brief, queued_clips, mix_sources, sources, thumbnails}
                        │
                        ▼
             [Taskiq worker --workers 1]
                        ├─ yt-dlp potong video / download_video_full ke download/
                        ├─ FFmpeg crop 9:16 + scale 720x1280
                        ├─ _generate_thumbnail() per klip → download/thumbnails/*.jpg
                        ├─ MediaPipe layout (fallback center-crop jika solutions tidak ada)
                        ├─ MoviePy subtitle dinamis + B-Roll (jika PEXELS_API_KEY ada)
                        └─ output/FINAL_<judul>.mp4 atau output/MIX_<judul>_*.mp4
```

### 2.2 Alur pemilihan model (agent)

```text
plan_shorts()
  └─ agent_llm(interactive=False, provider=?, model=?)
       └─ resolve_provider_model(provider, model)
            1. argumen request (provider/model)
            2. env AGENT_PROVIDER + AGENT_MODEL
            3. discover_models() → paket langchain_* terpasang
            4. gagal → error 503 + pesan "Cek AGENT_PROVIDER/AGENT_MODEL di .env"

select_agent_model.py / select_provider_model()   ← CLI/manual
      ├─ cari model LIVE dari API provider (key ada) + katalog
      ├─ tampilkan "nomor → provider/model"
      ├─ pilih nomor → init_chat_model(model, model_provider=...)
      ├─ tidak ada / ingin lain → input manual "provider/model"
      └─ hasil disimpan ke .env (AGENT_PROVIDER + AGENT_MODEL)
```

### 2.3 Alur environment

```text
process env (paling menang)
   ↓
backend/.env   (API & script)
workers/.env   (worker)
   ↓
.env (root)    ← fallback bersama
```

Semua dibaca oleh `backend/core/env.py::load_env(component)`. **Jangan** pakai `load_dotenv` langsung di modul baru.

---

## 3. Cara-caranya (How-to)

### 3.1 Prasyarat lokal

```powershell
uv --version          # 0.12.x
python --version      # 3.14.x (di-lock .python-version)
ffmpeg -version       # 8.x
psql --version        # PostgreSQL 18.x
```

Layanan lokal yang sudah teridentifikasi:
- PostgreSQL `localhost:5432` → user `postgres`, password `password`, DB `clip_ai`
- RabbitMQ `localhost:5672` via Docker (lihat [`RABBITMQ.md`](RABBITMQ.md))
- FFmpeg/FFprobe 8.1.1 di `PATH`

### 3.2 Setup awal (sekali)

Dari **root repo**:

```powershell
uv sync

# .env sudah disiapkan (SECRET_KEY acak + DB/RabbitMQ lokal). Isi API key:
# minimal AGENT_PROVIDER + AGENT_MODEL + key provider itu (lihat docs/API_KEYS.md).
notepad .env

# Buat tabel DB (init_db dipanggil saat API start / seed)
uv run python -m backend.scripts.seed_db --reset
```

Login Google: email harus tercantum di `OWNER_EMAILS` (`.env`). Seed hanya membuat satu user.

### 3.3 Jalankan API + worker

```powershell
# Terminal 1 — API
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — worker render (Windows wajib --workers 1)
uv run taskiq -A workers.worker:taskiq_app worker --loglevel=info --workers 1

# Opsional — monitor
uv run taskiq -A workers.worker:taskiq_app taskiq monitoring
```

Swagger: <http://127.0.0.1:8000/docs>

### 3.4 Dapatkan token

```powershell
# Dapatkan id_token dari frontend Google OAuth, lalu:
$TOKEN = (Invoke-RestMethod -Uri http://127.0.0.1:8000/auth/google -Method Post `
  -Body (@{ id_token='<GOOGLE_ID_TOKEN>' } | ConvertTo-Json) -ContentType 'application/json').access_token
```

### 3.5 Mode A — Brief saja (tanpa render)

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/agent/shorts -Method Post `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType 'application/json' `
  -Body (@{ topic='tips editing video'; platform='reels'; max_clips=3 } | ConvertTo-Json)
```

Balasan:

```json
{
  "status": "brief",
  "brief": {
    "platform": "reels",
    "topic": "tips editing video",
    "clips": [
      { "start_time": 5, "end_time": 20, "hook": "...", "title": "...", "caption": "...", "hashtags": ["#shorts"] }
    ],
    "style_notes": "..."
  }
}
```

### 3.6 Mode B — Brief + render video sungguhan

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/agent/shorts -Method Post `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType 'application/json' `
  -Body (@{
    topic='momen seru bola'
    video_url='https://www.youtube.com/watch?v=...'
    render_video=$true
    platform='tiktok'
  } | ConvertTo-Json)
```

Balasan:

```json
{
  "status": "processing",
  "task_id": "...",
  "brief": { "...": "..." },
  "queued_clips": 3
}
```

Cek hasil:

```powershell
Get-ChildItem output\*.mp4
ffprobe -v error -show_entries stream=width,height -of csv=p=0 output\FINAL_*.mp4
# harus 720,1280 (9:16)
```

### 3.7 Pilih provider/model manual (CLI)

```powershell
uv run python -c "from backend.services.model_discovery import select_chat_model; print(select_chat_model())"
```

Atau tetap di API lewat field `provider` / `model` pada body request. Katalog mencakup:
`cartesia, camb, openai, gemini, anthropic, openroute, openrouter, cloudflare, grok, groq, meta/muse, glm, minmax, kimi, deepseek, mistral, ollama, huggingface`.

### 3.8 Smoke render FFmpeg lokal (tanpa API key)

Berguna untuk memastikan pipeline render jalan tanpa provider eksternal:

```powershell
# 1. video uji 6 detik
ffmpeg -y -f lavfi -i "testsrc=size=1280x720:rate=30:duration=6" `
       -f lavfi -i "sine=frequency=440:duration=6" `
       -c:v libx264 -preset ultrafast -c:a aac -shortest temp\sample_input.mp4

# 2. render sungguhan (transkrip via Camb STT, B-Roll via Pexels)
uv run python scripts/smoke_render.py

# 3. verifikasi
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 output\FINAL_Smoke_Render_Lokal.mp4
```

Hasil terverifikasi: MP4 H.264 720×1280, 30 fps, AAC, ~6 detik.

### 3.9 Gate & test

```powershell
uv run python scripts/gate.py

# test tunggal
uv run pytest tests/test_agent_shorts.py -q
uv run pytest tests/test_no_model.py -q
```

Gate menjalankan: ruff check → ruff format --check → `docs/openapi sync` → compileall → PostgreSQL ping → pytest → import `backend.main` → import `workers.worker`.

---

## 4. Aturan pengembangan (ringkas)

- Python dari **root repo** dengan **uv**; tidak boleh `pip install`.
- `pyproject.toml` + `uv.lock` sumber dependensi; `backend/requirements.txt` legacy.
- Env lewat `load_env(...)` di `backend/core/env.py`; jangan `load_dotenv` langsung.
- UUID baru pakai `uuid.uuid7()`.
- Scoring viral **rule-based**; dilarang menambah jalur model/training.
- Setiap perubahan route/schema/auth/status → update `docs/API.md` + tabel API di `README.md`.
- Setiap fitur backend → test di `tests/**`; gate harus hijau.
- Jangan commit `.env`, `*.pkl`, `temp/`, `output/`, `logs/`, media.

---

## 5. Troubleshooting

| Gejala | Penyebab | Solusi |
| --- | --- | --- |
| `SECRET_KEY tidak aman atau belum diset` | placeholder / kosong | Isi `SECRET_KEY` acak di `.env` |
| `503 Provider LLM agent belum siap` | API key provider kosong / paket `langchain_*` belum terpasang | Isi key sesuai `AGENT_PROVIDER`, atau jalankan `select_chat_model()` |
| `422 video_url wajib` | `render_video=true` tanpa URL | Tambahkan `video_url` atau set `render_video=false` |
| Worker tidak terhubung broker | `RABBITMQ_URL` salah / container RabbitMQ mati | Cek `docker compose ps` dan `RABBITMQ_URL` — lihat [`RABBITMQ.md`](RABBITMQ.md) |
| `mp.solutions` tidak ada | MediaPipe 1.2.3 menghapus legacy solutions | Sudah ada fallback center-crop di `video_engine.py`; render tetap jalan |
| B-Roll tidak muncul | `PEXELS_API_KEY` kosong | Isi key; fungsi otomatis return False tanpa key |
| Transkrip gagal | Semua key STT kosong | Isi `CAMB_API_KEY` (STT utama) atau `OPENAI_API_KEY`/`GROQ_API_KEY` cadangan |

---

## 6. Ringkasan singkat (cheat sheet)

```powershell
uv sync
# isi .env (minimal AGENT_PROVIDER/AGENT_MODEL + key provider)
uv run python -m backend.scripts.seed_db --reset
uv run uvicorn backend.main:app --reload --port 8000          # terminal 1
uv run taskiq -A workers.worker:taskiq_app worker --workers 1    # terminal 2
uv run python scripts/gate.py                                # sebelum selesai
```

Endpoint kunci: `POST /auth/google`, `POST /agent/shorts`, `GET /tools/model-status`, `POST /tools/feedback`.
Output video: `output/FINAL_<judul>.mp4`. Kontrak lengkap: [`API.md`](API.md).
