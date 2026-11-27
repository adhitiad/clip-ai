# 🎬 Clip AI — Autonomous Content Factory

Backend SaaS untuk mengubah tren Google/YouTube menjadi klip vertikal: niche discovery, transkripsi, pemilihan hook, prediksi viral, subtitle dinamis, B-Roll, dubbing AI, dan rendering via antrean RabbitMQ (Taskiq + worker AMQP). **Dipakai secara lokal saja — tidak di-deploy ke server/VPS/cloud mana pun.**

Repo ini berisi **FastAPI backend + Taskiq worker + frontend TanStack Start** (`frontend/`, bun/bunx). Login **Google-only**, satu user (project pribadi). Semua perubahan Docker dilakukan oleh pemilik repo; agent hanya mengerjakan kode & gate.

## Isi Repo

| Path | Peran |
| --- | --- |
| `backend/main.py` | Entrypoint FastAPI, lifespan init DB/vector store, registrasi router |
| `backend/routes/` | HTTP API: auth, bridge, agent, clips, niche, tasks, tools, dashboard, ops, settings, youtube (tanpa billing) |
| `backend/core/` | Auth/JWT Google, request ID, env loader, model internal `@dataclass` |
| `backend/services/` | Viral scoring rule-based, video engine (MoviePy/FFmpeg + thumbnail), dubbing, Pinecone, model discovery, video discovery lintas sumber, access log MongoDB |
| `backend/utils/` | DB, YouTube/yt-dlp, RSS, captioning, B-Roll, Exa, Groq |
| `workers/worker.py` | Taskiq broker + task render `process_all_clips_task` |
| `backend/scripts/` | `seed_db.py`, `setup_assets.py` |
| `tests/` | 143 test: unit, kontrak OpenAPI, auth Google, dataclass/numpy/pandas, rotasi log, video discovery, access logger, render mix |
| `frontend/` | UI shonen neon gelap (`/shorts`, `/dashboard`, `/backend`, dll) + provider ber-icon (TanStack Start, bun) |
| `scripts/gate.py` | Gate Python lengkap (lint, format, compile, **koneksi PostgreSQL**, test, import smoke) |
| `docs/API.md` | Kontrak endpoint dan aturan akses |
| `docs/GOAL.md` | Tujuan, workflow end-to-end, dan cara menjalankan agent |
| `docs/CI_CD.md` | Workflow GitHub Actions, issue & discussion template |
| `docs/RABBITMQ.md` | Broker AMQP: worker primary + Taskiq worker (tanpa Redis) |
| `docs/TASKS.md` | Roadmap project pribadi (Google-only, tanpa role/plan/kredit) |
| `docs/PERSONAL.md` | Mode pribadi: akses, yang dihapus, env, verifikasi |
| `docs/VOICE.md` | Pemisahan LLM / TTS / STT + selector env |
| `docs/DATA-MODELS.md` | Model internal @dataclass + numpy/pandas |
| `docs/DOCKER.md` | Stack Docker: RabbitMQ 4, PostgreSQL 19, API + worker |
| `docs/RUNBOOK.md` | Cara start/stop, ganti provider, backup/restore, troubleshooting |
| `docs/UAT.md` | 17 skenario uji penerimaan pribadi |
| `docs/SECURITY-SCAN.md` | Hasil & cara scan OWASP ZAP lokal |
| `docs/API_KEYS.md` | Status pemakaian semua API key & mana yang wajib |
| `docs/OBSERVABILITY.md` | Trace W3C `traceparent`, log JSON, OTLP opsional |
| `docker-compose.yml` | Compose lokal (port host 6380/5433) |
| `.github/` | CI gate, CD artifact, ISSUE_TEMPLATE, DISCUSSION_TEMPLATE |

## Arsitektur

```text
Client -> FastAPI (backend.main:app)
              |-- PostgreSQL (SQLAlchemy, create_all + kompatibilitas manual)
              |-- RabbitMQ -> worker AMQP (primary) + Taskiq worker (fallback)
              |              `-> yt-dlp -> FFmpeg/MoviePy -> output/
              `-- LangChain LLM, Exa/Tavily/Firecrawl/Selenium, Cartesia/Camb/gTTS, Pexels, Pinecone, MongoDB access log
```

Alur auto-queue: `POST /niche/analyze-and-queue` → Google Trends RSS → LLM (LangChain) → cari video YouTube (yt-dlp) → transkrip via Camb STT → simpan clip → antre render Taskiq / worker AMQP. Project pribadi: tanpa kredit.

> **Jalankan semua perintah dari root repo.** Import memakai paket `backend.*`/`workers.*` dan banyak path relatif ke CWD (`temp/`, `models/`, `output/`, `logs/`, `download/`). `python backend/main.py` tidak didukung; gunakan `uvicorn backend.main:app`.

## Prasyarat

- **Python 3.14.x** — versi dikunci di `.python-version` dan `pyproject.toml` (`>=3.14,<3.15`).
- **uv** — satu-satunya package manager yang didukung. Jangan memakai `pip install`.
- **PostgreSQL** — buat database lebih dulu, mis. `CREATE DATABASE clipper_db;`.
- **RabbitMQ** — antrean `shorts-render` (primary) + broker Taskiq; hasil task di `task_results` (PostgreSQL + cache).
- **FFmpeg + FFprobe** — harus ada di `PATH` (`ffmpeg -version`).
- Semua LLM lewat **LangChain**: pilih `AGENT_PROVIDER` + `AGENT_MODEL` (openai, gemini, anthropic, openroute, cloudflare, grok, meta/muse, glm, minmax, kimi, deepseek, mistral, ollama, dll) lalu isi key provider itu.
- Transkripsi via Whisper REST (OpenAI → Groq cadangan); TTS: Cartesia → Camb AI → gTTS. Exa/HF/Pinecone/Pexels hanya mengaktifkan fitur opsional. ElevenLabs tidak dipakai.

## Setup

```powershell
uv sync

# Root .env adalah baseline; backend/.env menimpa nilai yang sama.
Copy-Item .env.example .env
# Edit SECRET_KEY (wajib, jangan pakai placeholder), DATABASE_URL, GROQ_API_KEY, dll.

# Migrasi skema (Alembic; membaca DATABASE_URL dari .env)
uv run alembic upgrade head

# Seed satu user pribadi dari OWNER_EMAILS
uv run python -m backend.scripts.seed_db --reset

# Pilih AGENT_MODEL (cari model tersedia; jika tidak ada, ketik manual provider/model)
uv run python scripts/select_agent_model.py
```

Urutan environment: **process env → `backend/.env` atau `workers/.env` → root `.env`**. API membaca `backend/.env`, worker membaca `workers/.env`, keduanya fallback ke root `.env`.

RabbitMQ memakai satu `RABBITMQ_URL` (`amqp://guest:guest@localhost:5672//` default). Lihat [`docs/RABBITMQ.md`](docs/RABBITMQ.md) untuk antrean `shorts-render`, worker AMQP, dan Taskiq worker.

### Menjalankan

```powershell
# Terminal 1 — API (dari root repo)
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — worker render
$w = uv run python scripts/worker_count.py; uv run taskiq worker workers.worker:broker --workers $w --ack-type when_saved

```

Di Windows `--workers 1` wajib agar render stabil; konsekuensinya task diproses satu per satu. Di Linux/macOS prefork boleh dipakai. Swagger: <http://127.0.0.1:8000/docs>.

### Database & Scoring

- **Alembic** mengelola perubahan skema (`uv run alembic upgrade head`). `init_db()` hanya `create_all` untuk runtime; tidak ada `ALTER TABLE` ad-hoc. Model baru wajib terdaftar di `_import_models()` (`backend/utils/db.py`).
- Scoring viral sepenuhnya **rule-based** (`backend/services/viral_predictor.py`). Tidak ada file `.pkl`, training data, atau proses training/retrain.
- Feedback performa nyata (`POST /tools/feedback`) hanya dicatat untuk analitik.

## Gate Python

```powershell
uv sync
uv run python scripts/gate.py
```

Gate menjalankan: `ruff check` → `ruff format --check` → `compileall` → **koneksi PostgreSQL** → `pytest` → import `backend.main` → import `workers.worker`.

Gate memakai **PostgreSQL** (default `postgresql://postgres:password@localhost:5432/clip_ai`), bukan SQLite. Pastikan server & database tersedia. Bisa diganti lewat `GATE_DATABASE_URL` (dipakai GitHub Actions dengan service `postgres:19`). RabbitMQ/API key tidak diperlukan untuk gate.

Test tunggal:

```powershell
uv run pytest tests/test_viral_predictor.py -q
uv run pytest tests/test_contracts.py::test_worker_exports_render_task -q
```

`backend/test_system.py` bukan pytest; itu smoke manual yang membutuhkan PostgreSQL hidup.

## API Singkat

| Grup | Endpoint utama | Akses |
| --- | --- | --- |
| Auth | `POST /auth/google`, `GET /auth/me` | Google ID token / Bearer JWT (tanpa password, 1 user) |
| Health | `GET /health/live`, `GET /health/ready` | publik, untuk Docker healthcheck |
| Shorts agent | `POST /agent/shorts` · UI `/shorts` | login (Google) | brief JSON; `render_video=true` + URL video → antre render mp4; beberapa URL (>4 menit) → satu mp4 mix; tanpa URL, AI otomatis cari video dari `topic` (2-10 vid >4 menit) |
| Clips | `POST /clips/generate-clips`, `POST /clips/feedback`, `GET /clips`, `GET\|PATCH\|DELETE /clips/{clip_id}` | login |
| Niche | `GET /niche/trending`, `GET /niche/suggest`, `GET /niche/find-videos`, `GET /niche/search-web` | login |
| Auto pipeline | `POST /niche/analyze-and-queue` | login |
| Tools | `POST /tools/dub`, `POST /tools/viral-score`, `GET /tools/providers`, `GET /tools/platforms`, `GET /tools/model-status`, `POST /tools/feedback` | login |
| Dashboard | `/dashboard/overview`, `/history`, `/profile`, `/stats`, `/health` | login |
| Revenue | `GET /revenue/summary`, `GET /revenue/advice` | login | ringkasan pendapatan platform (read-only) + saran AI dari model teks `AGENT_*` |
| Operations | `/ops/tasks`, `/ops/queue`, `/ops/cache`, `/ops/traces`, `/ops/workers`, `/ops/export`, `/ops/data`, `/ops/audit`, `/ops/access-log`, `/ops/health`, `/ops/render` | login | task, antrean, cache, trace, worker, ekspor/hapus data, audit AI, access log identitas, health, enqueue manual |
| Settings | `GET\|PATCH /settings/me`, `GET\|PATCH /settings/owner` | login | profil & preferensi pribadi |
| YouTube | `/youtube/search`, `/youtube/scheduler/*` | login / `X-Cron-Secret` | riset video + scheduler (env `YOUTUBE_*`) |
| Internal | `POST /auth/bridge` (hidden) | `AUTH_BRIDGE_TOKEN` | server-ke-server: session frontend → JWT backend |
| Tasks | `GET /tasks/{task_id}` | login | status task render (polling UI) |

Setiap respons memiliki header **`X-Request-ID`** (UUIDv7); ID sama dipakai log API & worker.

Kontrak lengkap ada di [`docs/API.md`](docs/API.md).

## Gate Frontend & Docker

```powershell
cd frontend
bun install
bun --bun run lint
bun --bun run check
bun --bun run typecheck
bun --bun run test
bun --bun run build
```

**Docker dijalankan oleh pemilik repo.** Agent tidak menjalankan/rebuild container;
perubahan `Dockerfile`/`docker-compose.yml` harus dijalankan sendiri. Lihat
[`docs/DOCKER.md`](docs/DOCKER.md) & [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Batasan yang Diketahui

- Project pribadi: satu user Google (`OWNER_EMAILS`), tanpa role/plan/kredit/billing.
- Tidak ada model ML/training; scoring viral rule-based; model internal `@dataclass` + numpy/pandas.
- Billing/Stripe & auto-publish TikTok/YouTube tidak diimplementasikan.
- Alembic sudah dipakai (`0001`–`0010`, termasuk `task_results`/`attempts`, penghapusan finance/investment, dan index query); CI/CD di `.github/workflows/` ([`docs/CI_CD.md`](docs/CI_CD.md)).
- Security scan memakai **OWASP ZAP lokal**, bukan Strix ([`docs/SECURITY-SCAN.md`](docs/SECURITY-SCAN.md)).
- Gate Python memakai PostgreSQL nyata (DB `clip_ai`); pytest langsung memakai SQLite hermetik.

## CI/CD, Issue & Discussion

Repo ini menggunakan GitHub Actions untuk CI gate dan CD artifact:

| File | Peran |
|------|-------|
| `.github/workflows/ci.yml` | CI gate: Python gate (ruff, format, compile, PostgreSQL, pytest, import) + frontend gate (typecheck, lint, prettier, vitest, E2E) |
| `.github/workflows/cd.yml` | CD: build Docker image & push artifact |
| `.github/workflows/security-zap.yml` | OWASP ZAP authenticated security scan (0 alert target) |
| `.github/ISSUE_TEMPLATE/` | Template laporan bug & fitur baru |
| `.github/DISCUSSION_TEMPLATE/` | Template Q&A, ide, dan show-and-tell |

Cara mengajukan issue atau diskusi:

- **Bug report**: gunakan template di `.github/ISSUE_TEMPLATE/bug_report.yml`, sertakan langkah reproduksi, log error, dan `X-Request-ID` jika tersedia.
- **Feature request**: gunakan `.github/ISSUE_TEMPLATE/feature_request.yml`, jelaskan use case dan endpoint yang terlibat.
- **Diskusi umum / Q&A / ide**: gunakan template di `.github/DISCUSSION_TEMPLATE/`.

Semua perubahan `Dockerfile`/`docker-compose.yml` dilakukan oleh pemilik repo; agent hanya mengerjakan kode & gate.

## Lisensi

MIT — lihat [`LICENSE`](LICENSE).
