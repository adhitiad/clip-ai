# Backend — Clip AI

FastAPI service untuk pipeline klip AI. Setup lengkap, env, dan gate ada di [README root](../README.md); dokumen ini fokus pada isi `backend/`.

## Menjalankan

Dari **root repo** (bukan dari `backend/`):

```powershell
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```

`SECRET_KEY` wajib diisi dan tidak boleh placeholder. API membaca `backend/.env`, lalu fallback ke `.env` root; process env selalu menang. Lihat `.env.example` untuk daftar variabel.

## Peta Modul

| Modul | Tanggung jawab |
| --- | --- |
| `main.py` | App FastAPI, lifespan, registrasi router (auth, bridge, agent, clips, niche, tasks, tools, dashboard, ops, settings, youtube) |
| `core/env.py` | Loader `.env` terpusat (root + component) |
| `core/auth.py` | Google-only login (`POST /auth/google` ID token + whitelist `OWNER_EMAILS`), JWT HS256, `get_current_active_user`, `get_db` |
| `core/security.py` | `require_owner` (semua user login = pemilik project pribadi) |
| `core/request_id.py` | Contextvar `X-Request-ID` (UUIDv7) + middleware/log |
| `core/telemetry.py` | Trace W3C `traceparent`, log JSON `logs/trace.jsonl`, OTLP opsional |
| `core/audit.py` | Audit panggilan AI ke `logs/audit.jsonl` (tanpa secret) |
| `core/taskiq_config.py` | Broker Taskiq (`AioPikaBroker`) + result backend |
| `core/worker_count.py` | Jumlah worker dari inti fisik (min 1 (genap untuk 2+ core)), override `TASKIQ_WORKERS` |
| `core/task_results.py` | Hasil & progres task: PostgreSQL `task_results` + cache memori |
| `routes/ops.py` | Endpoint operasional: tasks, queue, cache, trace, render |
| `routes/settings.py` | Endpoint pengaturan user & owner |
| `models/task_result.py` | Model SQLAlchemy `task_results` |
| `models/feedback.py` | Feedback performa untuk kalibrasi skor |
| `core/rabbitmq_config.py` | Resolver `RABBITMQ_URL` (broker AMQP), healthcheck |
| `core/validation.py` | Validasi & konfineness path (mis. `/tools/dub`) |
| `core/rate_limit.py` | Rate limit per endpoint |
| `core/models.py` | Model internal `@dataclass` (`ViralFeatures`, `ViralScore`, `ShortsPlan`, `ProviderInfo`, `ClipStat`, `RevenueSnapshot`) + numpy/pandas |
| `core/ai_pipeline.py` | Transkripsi STT → hook LLM → dubbing TTS → render |
| `core/agent.py` | Rencana short/reel/tiktok via LLM + `ShortsPlanData`; `clip_duration_stats` via numpy |
| `services/model_discovery.py` | Katalog provider LLM/TTS/STT + autodetection + `select_agent_model.py` |
| `services/provider_health.py` | Circuit breaker provider: 2 gagal → cooldown 60 detik |
| `services/tts.py` | TTS provider (Cartesia → Camb AI → gTTS; `TTS_PROVIDER`) |
| `services/transcription.py` | STT provider (Camb AI → OpenAI → Groq; `STT_PROVIDER`) |
| `services/viral_predictor.py` | Feature extraction + `rule_based_score` (numpy) + batch via pandas |
| `services/render_cache.py` | Hash input render + manifest artefak (`output/manifest.json`), ffprobe metadata |
| `services/render_pipeline.py` | Pipeline render bersama dipakai Taskiq & CLI `render_job.py` |
| `services/content_intelligence.py` | Analisis video, merge brief + trend, skor viral |
| `services/platform_revenue.py` | Adapter pendapatan YouTube/TikTok/Meta Reels (read-only, platform tanpa API → `available:false`) |
| `services/revenue_advice.py` | Saran peningkatan pendapatan via model teks `AGENT_*` (LangChain, override `REVENUE_AI_MODEL`) |
| `services/video_discovery.py` | Auto-discover video dari topik: YouTube + Exa/Tavily/Firecrawl/Selenium-BeautifulSoup + AI seleksi relevansi |
| `services/access_logger.py` | Access log identitas per-request ke MongoDB (`MONGODB_URL`), klasifikasi user/asing/hacker + flag |
| `core/rotating_jsonl.py` | Rotasi ukuran + redaksi secret untuk `trace.jsonl`/`audit.jsonl` |
| `utils/youtube_token.py` | Dekripsi token OAuth YouTube dari file frontend + refresh |
| `services/video_engine.py` | Layout MediaPipe, cut/crop FFmpeg, caption MoviePy, B-Roll, generate thumbnail per klip ke `download/thumbnails/` |
| `services/dubbing.py` | Transkripsi → terjemah → TTS → merge audio |
| `services/vector_store.py` | Pinecone + embeddings Ollama lokal (`OLLAMA_EMBED_MODEL`, offline) |
| `utils/db.py` | Engine/session, `init_db`, helper clip |
| `utils/youtube.py` | Subtitle/audio/segmen video via yt-dlp |
| `utils/rss_google.py` | Google Trends RSS + pencarian YouTube |
| `utils/captioning.py` | Word-level transcript dan SRT |
| `scripts/` | Seed DB, `render_job.py` (dipanggil worker AMQP), unduh aset demo |

## Router dan Akses

| Prefix | Isi | Catatan akses |
| --- | --- | --- |
| `/auth` | google, me | Google ID token + whitelist `OWNER_EMAILS` |
| `/auth/bridge` | — | `AUTH_BRIDGE_TOKEN`; server-ke-server: session frontend → JWT backend |
| `/agent` | shorts | login; brief default, render via `render_video=true`; multi-URL → mix satu MP4 lewat Taskiq; tanpa URL, AI auto-discover video dari `topic` |
| `/clips` | generate-clips, feedback, CRUD (`/clips`, `/clips/{id}`) | login |
| `/niche` | trending, suggest, find-videos, search-web, analyze-and-queue | login |
| `/tools` | dub, viral-score, providers, model-status, feedback | login |
| `/dashboard` | overview, history, profile, stats, health | login (semua user login = pemilik) |
| `/revenue` | summary, advice | login | pendapatan platform (bukan billing) + saran AI dari model teks `AGENT_*` |
| `/youtube` | search, scheduler/status, scheduler/collect | search login; scheduler `X-Cron-Secret` |
| `/tasks` | `{task_id}` | status task Taskiq (polling render) | login |
| `/ops` | tasks, queue, cache, traces, export, data, audit, access-log, health, render | login | operasional & observability |
| `/settings` | me, owner | login | profil & preferensi pribadi |

Kontrak request/response: [`docs/API.md`](../docs/API.md). Semua endpoint `/dashboard`, `/tools`, dan `/ops` memakai `response_model`; snapshot skema ada di [`docs/openapi.json`](../docs/openapi.json).

## Auth (Personal Mode)

- Project pribadi: **satu user** Google via `POST /auth/google` (ID token, `GOOGLE_CLIENT_ID`, whitelist `OWNER_EMAILS`).
- Token JWT HS256 via `POST /auth/bridge` (`AUTH_BRIDGE_TOKEN`); Bearer token untuk semua endpoint.
- Tidak ada password, role, plan, kredit, billing, atau `/auth/token`, `/auth/register`, `/auth/bootstrap-owner`, `/auth/set-role`.

## Database

- `init_db()` menjalankan `Base.metadata.create_all` setelah patch enum/kolom lama (jika ada) via `_import_models()` di `backend/utils/db.py`.
- **Alembic** dipakai untuk perubahan skema: `uv run alembic upgrade head` (membaca `DATABASE_URL` lewat `backend/core/env.py`). Revisi `0001_initial` membuat 7 tabel, `0005_task_results` menambah tabel hasil task, `0006_task_results_attempts` menambah kolom `attempts`, `0007_drop_finance_investment` menghapus modul uang, `0008_performance_feedback` menambah tabel feedback, `0009_clip_created_at` menambah timestamp clip, `0010_query_indexes` menambah index query; upgrade idempoten. `init_db()` hanya `create_all` untuk runtime, tanpa `ALTER TABLE` ad-hoc. Model baru tetap wajib diimpor via `_import_models()` di `backend/utils/db.py` agar masuk metadata.
- `DATABASE_URL` default di kode selalu set eksplisit.

## Scoring Viral (tanpa model)

- `predict_viral_score()` hanya memakai `rule_based_score()`; confidence selalu `rule_based`.
- Tidak ada `.pkl`, training data, `train_model`, atau endpoint retrain.
- `GET /tools/model-status` melaporkan `enabled: false`; `POST /tools/feedback` hanya analitik.

## Catatan Teknis

- `backend/requirements.txt` adalah file legacy. Sumber dependensi yang benar adalah `pyproject.toml` + `uv.lock`; tambahkan dependensi lewat `uv add`.
- Rendering memakai MoviePy 2 (`with_*`, `resized`, `cropped`) dan FFmpeg eksternal. Caption default memakai font bawaan MoviePy/Pillow.
- `backend/test_system.py` adalah smoke manual (bcrypt + DB hidup), bukan bagian pytest.
- Gate backend: `uv run python scripts/gate.py` dari root.
