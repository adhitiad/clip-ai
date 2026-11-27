# Runbook Operasional — Clip AI (Pribadi)

Versi: 2026-11-24 · Scope: lokal saja, satu user, Google-only.
Lihat [`PERSONAL.md`](PERSONAL.md), [`TASKS.md`](TASKS.md), [`VOICE.md`](VOICE.md).

---

## 1. Prasyarat

| Kebutuhan | Versi / catatan |
| --- | --- |
| Python | 3.14.x (`.python-version`, `requires-python`) |
| uv | 0.12+ (satu-satunya package manager Python) |
| bun | frontend only (`bun`/`bunx`), jangan npm/pnpm |
| Docker Desktop | aktif; `docker info` harus sukses |
| PostgreSQL | 19 via Docker (host `localhost:5433`, DB `clip_ai`) atau lokal 18 (5432) |
| RabbitMQ | `rabbitmq:4-management-alpine` via Docker (host `5672`, UI `15672`) |
| Taskiq worker | `$w = uv run python scripts/worker_count.py; uv run taskiq worker workers.worker:broker --workers $w --ack-type when_saved` |
| FFmpeg/FFprobe | di `PATH` (`ffmpeg -version`) |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OWNER_EMAILS` |

---

## 2. Setup awal (sekali)

```powershell
# Dari root repo
uv sync
uv run python -m backend.scripts.seed_db --reset   # opsional: seed 1 user

# Pastikan .env & frontend/.env.local sudah terisi (kunci asli, jangan di-commit)
```

Checklist:
- [x] `.env` berisi `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `OWNER_EMAILS`, `DATABASE_URL`, `RABBITMQ_URL` (diverifikasi 2026-11-25).
- [x] `frontend/.env.local` berisi `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (diverifikasi 2026-11-25).
- [x] `uv run alembic upgrade head` → `0010_query_indexes (head)` (diverifikasi di DB 5433 & 5432).
- [ ] `docker compose up -d --build` → 6 service sehat (db, rabbitmq, api, worker, render-worker, frontend) — dijalankan pemilik repo, belum saya amati.

### Verifikasi migrasi produksi

Jalankan dari root repo dengan `DATABASE_URL` yang dipakai API (bukan SQLite):

```powershell
uv run alembic current
uv run alembic upgrade head
uv run alembic current
```

Hasil verifikasi 2026-11-25:

| Database | Sebelum | Sesudah |
| --- | --- | --- |
| `localhost:5433` (DB container Compose) | `0001_initial` | `0010_query_indexes (head)` |
| `localhost:5432` (DB host/gate) | `0009_clip_created_at` | `0010_query_indexes (head)` |

Cek indeks hasil `0010`:

```powershell
uv run python -c "from sqlalchemy import create_engine, inspect; import os; e=create_engine(os.environ['DATABASE_URL']); i=inspect(e); print({t: [x['name'] for x in i.get_indexes(t)] for t in ('task_results','performance_feedback','clips')})"
```

Yang harus muncul: `ix_task_results_status_updated_at`, `ix_performance_feedback_created_at`, `ix_clips_created_at`.

Catatan: `uv run alembic check` saat ini masih melaporkan drift antara metadata ORM dan riwayat migrasi (tabel `finance_*` lama, kolom `stripe_*`, dll.). Ini **bukan** bagian dari acceptance verifikasi produksi dan gate tidak menjalankannya; jangan membuat revisi autogenerate tanpa meninjau manual.

---

## 3. Start / stop

### Cara Docker (disarankan)
```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f api worker     # Ctrl+C untuk keluar log
docker compose down                   # stop, volume tetap ada
docker compose down -v                # HATI-HATI: hapus volume DB/RabbitMQ
```

### Cara lokal (tanpa Docker)
```powershell
# Terminal 1 — API
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — worker (Windows wajib --workers 1)
uv run taskiq -A workers.worker:taskiq_app worker --loglevel=info --workers 1

# Terminal 3 — frontend
cd frontend
bun --bun run dev
```

Port: API `8000` · frontend `3000` · Postgres host `5433` · RabbitMQ `5672` (UI `15672`).

---

## 4. Cek kesehatan

```powershell
# API
Invoke-RestMethod http://127.0.0.1:8000/docs        # 200
Invoke-RestMethod http://127.0.0.1:8000/openapi.json

# DB
$env:PGPASSWORD='password'; psql -h localhost -p 5433 -U postgres -d clip_ai -c '\dt'

# RabbitMQ
docker compose exec rabbitmq rabbitmq-diagnostics -q ping
docker exec clip-ai-rabbitmq rabbitmq-diagnostics -q status | Select-Object -First 5

# Docker
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter name=clip-ai

# Gate
uv run python scripts/gate.py
cd frontend; bun --bun run lint; bun --bun run check; bun --bun run typecheck; bun --bun run build
```

---

## 5. Ganti provider (LLM / TTS / STT)

```powershell
# LLM interaktif (cari model live + select + input manual; gratis didahulukan)
uv run python scripts/select_agent_model.py

# Atau manual di .env
# AGENT_PROVIDER=nvidia
# AGENT_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
# TTS_PROVIDER=auto     # cartesia | camb | gtts | auto
# STT_PROVIDER=auto     # camb | openai | groq | auto
```

Restart API & worker setelah mengubah env:
```powershell
docker compose up -d --force-recreate api worker
```

Aturan penting di [`VOICE.md`](VOICE.md): **STT mendengar, LLM berpikir, TTS berbicara**.

---

## 6. Operasional harian

| Kebutuhan | Perintah |
| --- | --- |
| Lihat log API | `docker logs -f clip-ai-api` |
| Lihat log worker | `docker logs -f clip-ai-worker` |
| Antrean RabbitMQ | Management UI `http://localhost:15672` → Queues |
| Bersihkan antrean | Management UI → Queues → `shorts-render` → Purge |
| Regenerate route frontend | `cd frontend && bun --bun run generate-routes` |
| Cek migrasi | `uv run alembic current` / `uv run alembic history` |
| Seed ulang user | `uv run python -m backend.scripts.seed_db --reset` |

### OAuth YouTube (T-19)

```powershell
# 1. Buka di browser (butuh YOUTUBE_OAUTH_* terisi di frontend/.env.local)
http://localhost:3000/api/youtube/oauth/start

# 2. Setelah consent Google, callback:
#    GET /api/youtube/oauth/callback?code=...
#    → token ditukar & disimpan terenkripsi (AES-256-GCM)
```

- Penyimpanan: `frontend/.data/youtube_tokens.json` (**gitignored**, mode `0600`).
- Kunci: `YOUTUBE_TOKEN_ENCRYPTION_KEY` (min. 32 karakter) — jangan pernah di-commit.
- Response callback **tidak mengandung token**, hanya status.
- Redirect URI harus persis sama dengan Google Cloud Console.
- Scope OAuth: `youtube.readonly`, `yt-analytics.readonly`, `yt-analytics-monetary.readonly`. Token lama tanpa scope monetary harus **ulangi OAuth** agar `/revenue/summary` bisa membaca `estimatedRevenue`.
- Unit test: `cd frontend && bun --bun run test` (enkripsi/dekripsi).

### Access log identitas (MongoDB opsional)

```dotenv
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=clip_ai_access
```

- Kosongkan `MONGODB_URL` untuk menonaktifkan; API tetap jalan normal dengan log file + task results PostgreSQL.
- Bila diset: semua log (trace/audit/access) **dan** hasil task Taskiq ditulis ke MongoDB; data inti (clip/user/setting) tetap di PostgreSQL. `GET /ops/traces`, `/ops/audit`, `/ops/access-log`, dan polling task membaca Mongo lebih dulu.
- Koleksi: `access_logs` (satu dokumen per request) dan `known_ips` (IP ever-seen + email).
- Data per request: `ip`, `email`, `user_type`, `device_id`, `device_name`, `browser`, `http_version`, `tcp`, `method`, `path`, `status`, `user_agent`, `request_id`, `traceparent`, `token_hash` (hash 8 char, bukan JWT asli).
- Klasifikasi: `user ✅` (JWT/OWNER_EMAILS), `** ⚠️` (anonim), `hacker ❌` (IP asing + auth gagal/UA mencurigakan), `error 🛑` (status ≥500).
- Format baris: `level - actor - tgl jam - keterangan - flag ⚠️|✅|❌|🛑`.
- Lihat via `GET /ops/access-log?limit=100&only_flagged=true` atau panel **Access Log (MongoDB)** di halaman `/backend`.
- Test: `uv run pytest tests/test_access_logger.py -q`.

### Embedding vector offline (Ollama)

```powershell
ollama pull all-minilm
# opsional: cek model lokal
Invoke-RestMethod http://localhost:11434/api/tags
```

- Default: `OLLAMA_EMBED_MODEL=embeddinggemma-2:570m` (768 dimensi), `OLLAMA_HOST=http://localhost:11434`, `PINECONE_DIMENSION=768`.
- Pinecone memakai `PINECONE_API_KEY` + `PINECONE_INDEX_NAME`; `HUGGINGFACEHUB_API_TOKEN` **tidak diperlukan lagi**.
- Ganti model: set `OLLAMA_EMBED_MODEL=<model>` dan `PINECONE_DIMENSION=<dimensi>`, lalu buat index baru. Index lama dengan dimensi berbeda akan dilewati (log warning).
- Bila Ollama mati, vector search otomatis kembali kosong (fallback DB), API tetap hidup.

### Backup & restore PostgreSQL (T-18)

```powershell
# Backup (default: backups/clip_ai_<tanggal>.dump)
powershell -File scripts/backup_db.ps1

# Restore ke DB uji (WAJIB nama mengandung "restore" atau gunakan -Force)
powershell -File scripts/restore_db.ps1 `
  -DumpFile backups/clip_ai_20261124_154703.dump `
  -TargetUrl postgresql://postgres:password@localhost:5432/clip_ai_restore_test
```

- `scripts/db_url.ps1` dipakai bersama untuk parse `DATABASE_URL` (password tidak pernah dicetak).
- Script menolak restore ke DB utama tanpa `-Force`.
- Folder `backups/` **gitignored** (berisi data sensitif).
- Bukti: restore ke `clip_ai_restore_test` menghasilkan 7 tabel + 1 user.

### Cache render & manifest artefak

- `output/manifest.json` menyimpan hash input render + metadata MP4 (durasi, codec, resolusi, ukuran) per job.
- Job dengan input identik **tidak dirender ulang**; task mengembalikan `cached: true` dan path file lama.
- Invalidasi: hapus `output/manifest.json` / MP4 yang bersangkutan, atau naikkan `ENGINE_VERSION` di `backend/services/render_cache.py` setelah mengubah pipeline render.
- File `*.tmp` di `output/` adalah tulisan sementara; abaikan bila ada.

---

## 7. Troubleshooting

| Gejala | Penyebab | Solusi |
| --- | --- | --- |
| `SECRET_KEY tidak aman atau belum diset` | placeholder/kosong | Isi `SECRET_KEY` unik di `.env` |
| `403 Email tidak diizinkan` | email bukan `OWNER_EMAILS` | Tambahkan email ke `OWNER_EMAILS`, restart API |
| `503 GOOGLE_CLIENT_ID belum dikonfigurasi` | env kosong | Isi Google OAuth di `.env` |
| `503 Provider LLM agent belum siap` | key provider kosong | Isi `NVIDIA_API_KEY` atau ganti provider |
| Worker tidak terhubung broker | `RABBITMQ_URL` salah / container mati | Cek health `rabbitmq` & `RABBITMQ_URL` |
| API 500 `libxcb.so.1` | Image tanpa lib X11 | Sudah diperbaiki di `Dockerfile` (ffmpeg + libxcb1) |
| `import cv2` gagal | opencv-contrib butuh X11 | `docker compose up -d --build api worker` |
| Transkrip kosong | semua key STT kosong | Isi `CAMB_API_KEY` / `OPENAI_API_KEY` / `GROQ_API_KEY` |
| Caption tidak muncul | STT tidak aktif | Cek log worker: `[STT] Segmen berhasil via ...` |
| `bun --bun run lint` error | script/config lama | Sudah diperbaiki di T-14: `eslint src` + ignore generated |

---

## 8. Escalation

Jika gate Python/frontend gagal setelah mengikuti runbook:
1. Catat output lengkap perintah yang gagal.
2. Pastikan versi Python 3.14 / uv 0.12 / bun terbaru.
3. Periksa `.env` tidak ter-commit dan tidak ada perubahan kode lokal yang belum tersimpan.
4. Buka issue dengan template **Bug report** di GitHub.
