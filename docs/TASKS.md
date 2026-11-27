# Roadmap Penyelesaian Sistem — Clip AI (Checklist)

Centang task di bawah **hanya setelah** kriteria diterima terpenuhi.
Format: `- [x]` selesai · `- [ ]` terbuka · `- [🔶]` sebagian (menunggu pihak/akun eksternal).

> Scope: **project pribadi, satu user, Google-only, tanpa role/plan/kredit/billing**.
> Lihat [`PERSONAL.md`](PERSONAL.md), [`GOAL.md`](GOAL.md), [`VOICE.md`](VOICE.md).

---

## 0. Master checklist

### Fase A — Stabilitas & pembuktian
- [x] **T-14** Gate frontend penuh hijau
- [x] **T-15** Runbook operasional
- [🔶] **T-16** UAT pribadi (17 skenario) — 13 lulus, 2 gagal, 2 blokir (lihat `docs/UAT.md`)
- [x] **T-21** Smoke render berulang 3×

### Fase B — Observability & ketahanan
- [x] **T-17** Logging berkorelasi (request ID)
- [x] **T-18** Backup & restore PostgreSQL
- [x] **T-19** OAuth YouTube penuh (code → token terenkripsi)

### Fase C — UX
- [x] **T-20** UI agent shorts end-to-end

### Selesai
- [x] **T-11** Validasi input & keamanan path
- [x] **T-12** Test backend ≥60
- [x] **T-13** Kontrak OpenAPI terkunci

---

## 1. Status sistem (checklist)

- [x] Auth Google: `/auth/google`, `/auth/me`, whitelist `OWNER_EMAILS`, JWT HS256
- [x] Database: Alembic `0001`–`0010`, 7 tabel, seed 1 user
- [x] RabbitMQ: `rabbitmq:4-management-alpine`, antrean `shorts-render` + Taskiq fallback
- [x] Docker: 6 service sehat (db, rabbitmq, api, worker, render-worker, frontend)
- [x] LLM: LangChain, default NVIDIA NIM, 17 provider, picker + gratis didahulukan
- [x] TTS: `backend/services/tts.py` (Cartesia → Camb → gTTS)
- [x] STT: `backend/core/transcription.py` (Camb → OpenAI → Groq)
- [x] Agent shorts: brief nyata + render E2E task SUCCESS, MP4 720×1280
- [x] Feedback: skor tersimpan, few-shot berubah, fallback DB
- [x] YouTube: Data API v3 + scheduler, kredensial dari `aivisio`
- [x] Validasi & rate limit: `core/validation.py`, `core/rate_limit.py`
- [x] Gate Python: **126 passed**, 0 warning, PostgreSQL nyata
- [x] Gate frontend penuh (lint/check/typecheck/test/**test:e2e**/build). `test:e2e`: 49 passed, exit 0.
- [🔶] Runbook & UAT (UAT.md terisi: 13/17 lulus)
- [x] Backup/restore DB
- [x] OAuth YouTube penuh
- [x] UI shorts

---

## 2. Peta sistem

```
[Frontend TanStack Start]
  ├─ Google OAuth (Better Auth) ──▶ id_token ──▶ POST /auth/google ──▶ JWT
  ├─ /api/youtube/scheduler (X-Cron-Secret)
  └─ UI provider (LLM/TTS/STT ber-icon)

[Backend FastAPI]
  ├─ /agent/shorts ──▶ LLM (brief) ──▶ Taskiq ──▶ video_engine ──▶ MP4
  ├─ /tools/dub ──▶ STT ──▶ LLM ──▶ TTS ──▶ FFmpeg
  ├─ /niche/* ──▶ Google Trends + LLM + YouTube/Exa
  ├─ /youtube/* ──▶ YouTube Data API v3
  └─ /dashboard/* ──▶ statistik pribadi

[Infra lokal]
  PostgreSQL (clip_ai) · RabbitMQ 4 · Taskiq · FFmpeg · Docker Compose
```

---

## 3. Work breakdown (detail + checklist)

### Fase A — Stabilitas & pembuktian

- [x] **T-14 — Gate frontend penuh hijau** `P0`
  - Tujuan: `bun --bun run lint`, `check`, `typecheck`, `test`, `test:e2e`, `build` semua exit 0.
  - Masalah: `bunx eslint src` bersih, tetapi script `lint` (`eslint` tanpa argumen) error; file generated `src/paraglide/` dilaporkan error parser.
  - Langkah:
    - [x] Ubah script `lint` di `frontend/package.json` menjadi `eslint src`.
    - [x] Pastikan `frontend/eslint.config.js` mengabaikan `src/paraglide/**` dan `src/routeTree.gen.ts`.
    - [x] Jalankan `bun install` bila dependency berubah.
    - [x] Verifikasi keempat perintah gate frontend.
  - Berkas: `frontend/package.json`, `frontend/eslint.config.js`, `frontend/.prettierignore`.
  - Acceptance:
    - [x] 6 perintah exit 0, termasuk `test:e2e` (49 passed).
    - [x] Tidak ada error dari file generated.
  - Dependensi: none · Estimasi: 1–2 jam.
  - Risiko: perubahan config eslint bisa memunculkan error lama → perbaiki bertahap, jangan matikan aturan.

- [x] **T-15 — Runbook operasional** `P1`
  - Tujuan: sistem bisa dijalankan ulang hanya dengan mengikuti dokumen.
  - Buat `docs/RUNBOOK.md` berisi:
    - [x] Prasyarat: Python 3.14, uv, bun, Docker, FFmpeg, Postgres, RabbitMQ.
    - [x] Setup: `uv sync`, isi `.env` + `frontend/.env.local`, `alembic upgrade head`, `seed_db --reset`.
    - [x] Start/stop: Docker Compose vs lokal (`uvicorn` + `taskiq`).
    - [x] Cek sehat: `/docs`, `/dashboard/health`, `docker ps`, `rabbitmq-diagnostics -q ping`, `pg_isready`.
    - [x] Ganti provider LLM/TTS/STT via env + `select_agent_model.py`.
    - [x] Operasional harian: baca log, clear queue, regenerate route frontend.
    - [x] Backup/restore DB (link T-18).
    - [x] Troubleshooting 10 masalah umum.
  - Acceptance:
    - [x] Runbook dibuat & tautan ke docs lain benar.
    - [x] 5 perintah pertama dicoba berhasil.
  - Dependensi: none · Estimasi: 2 jam.
  - Risiko: dokumen cepat usang → cantumkan tanggal versi.

- [🔶] **T-16 — UAT pribadi** `P1` — hasil dicatat: 13 lulus, 2 gagal, 2 blokir
  - Tujuan: satu checklist manual membuktikan alur lengkap.
  - Buat `docs/UAT.md` dengan skenario:
    - [x] Login Google email whitelist → JWT; email luar whitelist → 403.
    - [x] `/auth/me` mengembalikan identitas.
    - [x] `/agent/shorts` brief (`render_video=false`) → hook/judul/hashtag masuk akal.
    - [x] `/agent/shorts` render (`render_video=true` + URL) → task SUCCESS, MP4 9:16.
    - [x] `/clips/feedback` → skor & few-shot berubah.
    - [x] `/tools/dub` dengan `script_text` → MP4 bersuara.
    - [x] `/tools/viral-score` → skor 1–10 + 10 features.
    - [x] `/niche/search-web` `search_type` invalid → 422.
    - [x] `/youtube/search` → hasil nyata.
    - [x] Endpoint AI tanpa token → 401; rate limit → error setelah kuota.
  - Acceptance:
    - [ ] 17/17 lulus — saat ini 13 lulus, 2 gagal, 2 blokir; detail di `docs/UAT.md`.
  - Dependensi: T-15 · Estimasi: 2–3 jam.
  - Risiko: butuh internet & kredensial aktif → siapkan fallback.

- [x] **T-21 — Smoke render berulang 3×** `P1`
  - Tujuan: render stabil, bukan kebetulan sekali jalan.
  - Langkah:
    - [x] Jalankan `scripts/smoke_render.py` 3× berturut.
    - [x] Jalankan 1× E2E API render.
    - [x] Catat ukuran & durasi tiap output.
  - Acceptance:
    - [x] 4/4 sukses.
    - [x] MP4 720×1280.
    - [x] Subtitle tidak kosong saat STT aktif.
  - Dependensi: none · Estimasi: 1 jam.
  - Risiko: B-Roll Pexels sesekali gagal → fallback tetap sukses.

### Fase B — Observability & ketahanan

- [x] **T-17 — Logging berkorelasi** `P1`
  - Langkah:
    - [x] Tambah `X-Request-ID` (UUIDv7) di middleware FastAPI.
    - [x] Teruskan request_id ke payload task Taskiq.
    - [x] Tampilkan di log API & worker dengan format konsisten.
  - Berkas: `backend/main.py`, `workers/worker.py`, `backend/routes/agent.py`, `backend/log.py`.
  - Acceptance:
    - [x] Satu alur brief→render punya request_id sama di log API & worker.
    - [x] Test `tests/test_request_id.py`.
  - Dependensi: none · Estimasi: 2 jam.
  - Risiko: jangan log token/API key.

- [x] **T-18 — Backup & restore PostgreSQL** `P1`
  - Langkah:
    - [x] Buat `scripts/backup_db.ps1` (`pg_dump` dari `DATABASE_URL`).
    - [x] Buat `scripts/restore_db.ps1` (`pg_restore`).
    - [x] Dokumentasikan di runbook.
  - Acceptance:
    - [x] Backup berhasil.
    - [x] Restore ke DB uji `clip_ai_restore_test` berisi 7 tabel & 1 user.
  - Dependensi: T-15 · Estimasi: 1–2 jam.
  - Risiko: jangan restore ke DB utama tanpa konfirmasi.

- [x] **T-19 — OAuth YouTube penuh** `P2`
  - Langkah:
    - [x] `GET /api/youtube/oauth/start` → redirect consent Google.
    - [x] `GET /api/youtube/oauth/callback` → tukar `code` → token.
    - [x] Enkripsi access/refresh token dengan `YOUTUBE_TOKEN_ENCRYPTION_KEY` (AES-256-GCM).
    - [x] Simpan token terenkripsi; putuskan & dokumentasikan lokasi penyimpanan.
  - Acceptance:
    - [x] Callback dengan code valid → token tersimpan.
    - [x] Tanpa key → 503.
    - [x] Token tidak muncul di log/response.
    - [x] Unit test enkripsi/dekripsi.
  - Dependensi: `YOUTUBE_OAUTH_*` terisi · Estimasi: 3–4 jam.
  - Risiko: redirect URI harus persis sama dengan Google Cloud Console.

### Fase C — UX

- [x] **T-20 — UI agent shorts** `P1`
  - Langkah:
    - [x] Halaman `/shorts`: form topic, platform, video_url, render_video.
    - [x] Tampilkan provider ber-icon dari `models.ts` (LLM/TTS/STT)。
    - [x] Tombol generate + tampilan brief JSON.
    - [x] Polling status task render.
  - Berkas: `frontend/src/routes/shorts.tsx`, `frontend/src/lib/shorts-api.ts`, komponen related.
  - Acceptance:
    - [x] Brief & render bisa dibuat dari UI.
    - [x] Token dari session Better Auth, bukan localStorage.
    - [x] Tidak ada secret via `VITE_`.
  - Dependensi: T-14 · Estimasi: 4–6 jam.
  - Risiko: simpan session di cookie HttpOnly.

---

## 4. Milestone (checklist)

- [🔶] **M1 — Sistem siap pakai lokal**: T-14, T-15, T-21 selesai; T-16 sebagian (13/17 lulus)
- [x] **M2 — Operasional & aman**: T-17, T-18, T-19 selesai
- [x] **M3 — Pengalaman lengkap**: T-20 selesai

## 5. Definition of Done global

- [x] Satu user, Google-only, tanpa password/role/plan/kredit/billing
- [x] Gate Python hijau (126 passed, 0 warning)
- [x] Gate frontend hijau penuh — `test:e2e` 49 passed, exit 0
- [🔶] Runbook tersedia; UAT tercatat di `docs/UAT.md` (13 lulus, 2 gagal, 2 blokir)
- [x] Backup/restore terbukti
- [x] OAuth YouTube penuh
- [x] UI shorts end-to-end
- [x] Semua docs sinkron (README, API, GOAL, PERSONAL, VOICE, DOCKER, RABBITMQ, OBSERVABILITY, API_KEYS, TASKS)

## 6. Cara kerja

Aturan tetap untuk setiap perubahan — **bukan checklist task**, jadi tidak memakai `- [ ]`:

- Ambil satu task ID berurutan (kecuali ada alasan).
- Buat branch dari `master` (`git checkout -b task/T-14`).
- Implementasi + test di `tests/**` (backend) / gate frontend.
- Update dokumen yang tersentuh.
- Jalankan gate Python & frontend.
- Centang task hanya setelah acceptance terpenuhi.
- Jangan tambah role/plan/kredit/billing atau model ML.

## 7. Perintah cepat

```powershell
# Backend
uv sync
uv run alembic upgrade head
uv run python -m backend.scripts.seed_db --reset
uv run python scripts/gate.py
uv run python scripts/select_agent_model.py

# Frontend
cd frontend
bun install
bun --bun run dev
bun --bun run lint
bun --bun run check
bun --bun run typecheck
bun --bun run test:e2e
bun --bun run test:a11y
bun --bun run build

# Docker
docker compose up -d --build
docker compose ps
docker compose logs -f api worker
# PC worker jarak jauh (isi dulu .env.worker)
docker compose -f docker-compose.worker.yml up -d --build
```

---

## 8. Backlog ide pengembangan (diurutkan dari yang paling penting)

Urutan = prioritas. **1–3 dikerjakan lebih dulu** (murah, langsung menutup celah yang sudah ditemukan). Baris **16–24** adalah hasil audit performa & health (2026-11-25), detailed di Fase D. Semua ide tunduk pada aturan yang ada: tanpa role/plan/kredit/billing, tanpa model ML/training, Docker dijalankan pemilik repo.

| # | Task | Mengapa penting | Langkah pertama |
| --- | --- | --- | --- |
| 1 | ✅ **Gate kontrak hidup** | Dokumen & OpenAPI sudah 3× tidak sinkron/ter-revert; ini akar masalahnya | `tests/test_docs_openapi_sync.py` sudah dibuat (3 test); langkah `docs/openapi sync` ditambah ke `scripts/gate.py` |
| 2 | ✅ **Helper E2E server fn** | Mock `x-tss-serialized` + seroval masih duplikat & rapuh; fondasi untuk UI test berikutnya | `frontend/tests/helpers/server-fn.ts` berisi `stubServerFn` + `mockProviders` + fixture; dipakai ulang di `shorts.spec.ts` & `navigation.spec.ts` |
| 3 | ✅ **Progress render nyata di `/shorts`** | Worker sudah kirim `PROGRESS {current,total}`, tapi UI hanya menampilkan "SUCCESS" | `GET /tasks/{task_id}` mengembalikan `progress {current,total,percent}`; UI menampilkan progress bar; `tests/test_task_status.py` + E2E progres |
| 4 | ✅ **ZAP scan dengan login** | Scan anonymous menghasilkan 92% 4xx; otorisasi data belum teruji | `scripts/zap_auth_scan.py`: SQLite terisolasi + JWT via `/auth/bridge` + replacer ZAP; spec OpenAPI terfilter + guard `scripts/zap_safe_app.py`; hasil **0 High/Medium/Low** di `docs/SECURITY-SCAN.md` |
| 5 | ✅ **Render idempoten + manifest artefak** | Smoke render 3× & E2E mengulang kerja yang sama; hasil sulit direproduksi | `backend/services/render_cache.py`: hash input + `output/manifest.json` (metadata ffprobe); worker skip render bila cache hit; `tests/test_render_cache.py` |
| 6 | ✅ **Observability API → worker + RabbitMQ** | `X-Request-ID` baru sebatas grep log; belum bisa dianalisis | `backend/core/telemetry.py` + `frontend/src/server/telemetry.ts`: `traceparent` W3C, log `logs/trace.jsonl`, OTLP opsional; `tests/test_telemetry.py` |
| 7 | ✅ **Intelegensi konten di worker** | Render tanpa analisis video/brief/trend/skor viral | `backend/services/content_intelligence.py`: `analyze_video` → `apply_brief_to_clips` → `score_clips`; payload job + span `content.*`; `tests/test_content_intelligence.py` |
| 8 | ✅ **Kesehatan queue & retry Taskiq** | Worker single-process di Windows; kegagalan render mudah lolos tanpa jejak | `SmartRetryMiddleware` (2 retry, jitter/backoff), DLQ `shorts-render-dlq`, kolom `attempts` di `task_results` + migrasi `0006`, error via `/tasks/{task_id}` & `/ops/queue` |
| 9 | ✅ **Katalog provider health & biaya** | 17 provider + NIM default; pemilihan masih statis free-first | `provider_health.py` (circuit breaker), `provider_metadata()` → `latency_hint`/`cost_tier`/`healthy`; auto-fallback saat unhealthy, manual override tetap menang; badge UI |
| 10 | ✅ **Kalibrasi skor viral tanpa ML** | Feedback baru analitik; bobot masih tetap, belum berbasis bukti | `VIRAL_SCORE_WEIGHTS` (10 angka 0–3) + `GET /tools/calibration` (korelasi pandas), tabel `performance_feedback` + migrasi `0008`, `tests/test_calibration.py` |
| 11 | ✅ **Lifecycle data pribadi** | Project satu user: kedaulatan data & jejak biaya itu fitur inti | `backend/core/audit.py` (`logs/audit.jsonl`, LLM/TTS/STT), `GET /ops/export`, `DELETE /ops/data` (konfirmasi `DELETE`), `GET /ops/audit`, `tests/test_lifecycle.py` |
| 12 | ✅ **Semua fitur punya endpoint** | Fitur tanpa HTTP API tidak bisa dipakai/diaudit | `routes/ops.py` (tasks, queue, cache, traces, render), `routes/settings.py`, CRUD Clip; `tests/test_endpoint_coverage.py` |
| 13 | ✅ **Pendapatan platform + saran AI** | Data pendapatan belum bisa dibaca dari backend; creator butuh arahan konkret | `services/platform_revenue.py` (YouTube Analytics; TikTok/Meta adapter `available:false`), `GET /revenue/summary`, `GET /revenue/advice` (model teks `AGENT_*`), panel dashboard; `tests/test_revenue.py` |
| 14 | ✅ **QueryClient defaults** | Refetch berulang saat fokus/navigasi | `frontend/src/integrations/tanstack-query/root-provider.tsx`: `staleTime: 30_000`, `retry: 1`, `refetchOnWindowFocus: false` |
| 15 | ✅ **Lazy load `/backend`** | 30+ endpoint GET dipanggil paralel saat halaman dibuka | Tombol "Muat data backend" mengaktifkan query; `frontend/src/routes/_protected/backend.tsx` |
| 16 | ✅ **Health publik & detail** | Docker healthcheck dan diagnosis butuh endpoint tanpa login | `/health/live`, `/health/ready`, `/ops/health`; `backend/routes/health.py`, `tests/test_health.py`, OpenAPI 46 path |
| 17 | ✅ **Code splitting bundle frontend** | `index` ±397 KB, chunk `card` ±357 KB, `queries` ±142 KB | Audit: chunk `card` 281 KB ternyata `@tanstack/react-db` dari `ModelBadge`, bukan UI Card. `ModelProviderGrid` kini lazy + defer di `/` dan `/shorts`; JS awal rute `/` ~967 KB → ~675 KB, entry `card` tinggal 1,5 KB |
| 18 | 🔶 **Better Auth env di runtime Docker** | Log dev: `Social provider google is missing clientId or clientSecret`, login berpotensi gagal | Env terverifikasi; DB `google_sub` + seed owner selesai; alur OAuth sudah mencapai Google dengan `client_id`/`redirect_uri` benar, tetapi Google menolak browser otomatis ("Browser atau aplikasi ini mungkin tidak aman"). Perlu browser normal pemilik |
| 19 | ✅ **Regression visual + aksesibilitas** | E2E 34 test belum punya screenshot snapshot dan axe | `frontend/e2e/visual-a11y.spec.ts` screenshot 14 rute + axe WCAG A/AA; job `frontend-a11y` di `ci.yml` |
| 20 | ✅ **Offload blocking call di route async** | DB/request sinkron di `async def` memblokir event loop | `asyncio.to_thread(...)` di agent/clips/niche/tools/dashboard + middleware; gate 126 test hijau |
| 21 | ✅ **Index DB pendukung query** | Sort/filter makin lambat saat data tumbuh | Migrasi `0010_query_indexes`: `ix_task_results_status_updated_at`, `ix_performance_feedback_created_at`, `ix_clips_created_at`; `alembic upgrade head` → head |
| 22 | ✅ **Response model OpenAPI bertahap** | Banyak respons masih `{}` di skema | 15 endpoint dashboard/tools/ops kini bertipe; `docs/openapi.json` di-regenerate. Sisa 13 skema `{}` di agent/clips/niche/tasks/youtube |
| 23 | ✅ **Rotasi log** | `logs/trace.jsonl` dan `logs/audit.jsonl` tumbuh tanpa batas | `backend/core/rotating_jsonl.py`: rotasi ukuran (default 5 MiB, 3 backup) + redaksi secret; `LOG_MAX_BYTES`/`LOG_BACKUPS`; `tests/test_log_rotation.py` |
| 24 | ✅ **Verifikasi migrasi produksi** | `init_db()` bukan pengganti Alembic | `uv run alembic upgrade head` → `0010_query_indexes (head)` di DB 5433 & 5432; hasil dicatat di `docs/RUNBOOK.md` |
| 25 | ✅ **Multi-worker lintas lokasi** | Satu broker RabbitMQ melayani worker di rumah, kantor, dan kafe; hasil render kembali ke UI melalui polling | Bind `10.10.8.160:5672`, UI tetap localhost; user `worker_kantor1`/`worker_kantor2`/`worker_rumah` dengan izin `^shorts-render.*$`; `.env.worker.kantor1`/`.env.worker.kantor2`/`.env.worker.rumah` + `docker-compose.worker.yml`; koneksi terverifikasi |
| 26 | ✅ **Mix klip dari beberapa video sumber** | Short dibuat dengan menggabungkan momen dari beberapa video orang lain (>4 menit), bukan satu sumber | `POST /agent/shorts` menerima `video_urls[]` + `mix_sources`/`min_source_seconds`; klip diambil per sumber, dipilih bergiliran, dirender per sumber lalu digabung jadi `output/MIX_*.mp4`; UI `/shorts` input multi-URL; multi-sumber lewat Taskiq; `tests/test_agent_shorts.py`, `tests/test_render_mix.py` |
| 27 | ✅ **Auto-discover video dari topik + thumbnail** | User hanya input `topic` (niche), AI cari 2-10 video (>4 menit) dari YouTube + Exa/Tavily/Firecrawl/Selenium+BeautifulSoup, pilih paling relevan via AI, unduh penuh ke `./download/`, generate thumbnail per klip, render jadi satu MP4 mix | `backend/services/video_discovery.py` (semua sumber, AI seleksi AGENT_*), `backend/utils/youtube.py::download_video_full`, `backend/services/video_engine.py::_generate_thumbnail`, route `GET /download/*`; `tests/test_video_discovery.py`; tanpa `topic` → `422` |
| 28 | ✅ **Embedding vektor Ollama `embeddinggemma-2:570m`** | Model embedding lokal di-ganti ke `embeddinggemma-2:570m` (768 dimensi) yang sudah di-pull; dimensi disesuaikan via `PINECONE_DIMENSION=768` | `.env` + `.env.example` + `docs/RUNBOOK.md` + `docs/API_KEYS.md`; `backend/services/vector_store.py` otomatis ambil dimensi dari index bila ada |
| 29 | ✅ **Access log identitas ke MongoDB** | Catat IP, email, jenis user, device id/name, browser, TCP, HTTP version tiap request; IP asing + auth gagal → ❌ hacker; error 500 → 🛑 | `backend/services/access_logger.py`, `backend/main.py` middleware, `GET /ops/access-log`, UI `/backend`; `pymongo`, `MONGODB_URL`/`MONGODB_DB`; format `level - actor - tgl jam - keterangan - flag`; `tests/test_access_logger.py` |

### Detail checklist audit performa & health (Fase D)

- [x] **D-01 — QueryClient defaults** `P1`
  - [x] `staleTime: 30_000`, `retry: 1`, `refetchOnWindowFocus: false`.
  - Berkas: `frontend/src/integrations/tanstack-query/root-provider.tsx`.
- [x] **D-02 — Lazy load `/backend`** `P1`
  - [x] Tombol "Muat data backend" sebelum 30+ query dijalankan.
  - Berkas: `frontend/src/routes/_protected/backend.tsx`.
- [x] **D-03 — Health endpoint** `P0`
  - [x] `/health/live`, `/health/ready`, `/ops/health`.
  - [x] Perbaikan `text("SELECT 1")` di `health.py`, `ops.py`, `dashboard.py`.
  - Berkas: `backend/routes/health.py`, `backend/routes/ops.py`, `tests/test_health.py`.
- [x] **D-04 — Code splitting frontend** `P2`
  - [x] Audit chunk `card`: 281 KB bukan shadcn Card, melainkan `@tanstack/react-db` dari `ModelProviderGrid`.
  - [x] Lazy + defer `ModelProviderGrid` di `/` dan `/shorts`; preload rute turun ~967 KB → ~675 KB.
  - Acceptance: initial bundle turun dan gate tetap hijau (49 e2e + build + typecheck + lint + format).
- [🔶] **D-05 — Better Auth Docker env** `P1`
  - [x] Pastikan `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` terbaca di container frontend.
  - [ ] Uji login Google nyata, bukan session tiruan — sudah dicoba: Google menolak browser otomatis meski `client_id`/`redirect_uri` benar; perlu browser normal milik pemilik + akun uji. Detail di `docs/UAT.md` UAT-01/02.
- [x] **D-06 — Visual & aksesibilitas** `P2`
  - [x] Playwright screenshot per rute publik/protected (14 rute).
  - [x] axe WCAG 2 A/AA di CI lewat job `frontend-a11y`.
- [x] **D-07 — Offload blocking call** `P1`
  - [x] `asyncio.to_thread(...)` untuk DB/request sinkron di route async.
  - [x] Gate Python tetap hijau (126 test).
- [x] **D-08 — Index DB** `P2`
  - [x] Migrasi baru `0010_query_indexes` untuk tiga index di atas.
  - [x] `uv run alembic upgrade head` berhasil → `0010_query_indexes (head)`.
- [x] **D-09 — Response model** `P2`
  - [x] `response_model` untuk 15 endpoint dashboard/tools/ops yang masih return dict.
  - [x] Snapshot OpenAPI di-regenerate; gate docs sync + 126 test hijau.
- [x] **D-10 — Rotasi log** `P2`
  - [x] Rotasi `trace.jsonl` dan `audit.jsonl` via `backend/core/rotating_jsonl.py` (ukuran + backup).
  - [x] Redaksi secret di kedua file; diuji `tests/test_log_rotation.py`.
- [x] **D-11 — Migrasi produksi** `P0`
  - [x] `0005`–`0010` terpasang via Alembic di DB 5433 & 5432 (`alembic current` → head).
  - [x] Dicatat lengkap di `docs/RUNBOOK.md` (termasuk indeks `0010` dan catatan drift `alembic check`).

### Fase E — Security findings & remediation (scan 2026-11-25)

Sumber: `uv run python securities/run_all.py --include-nuclei --allow-failure`,
`uv run python scripts/zap_auth_scan.py`, dan laporan di `securities/reports/`.
ZAP terautentikasi: **0 alert**. Status `[x]` hanya diberikan setelah
perbaikan + verifikasi runtime/scan + gate hijau. `[🔶]` = menunggu keputusan pemilik.

| ID | Temuan | Severity | Bukti | Cara perbaiki | Status |
| --- | --- | --- | --- | --- | --- |
| **E-01** | `pillow` 11.3.0 → 13.0.0 via override `[tool.uv]` (moviepy membatasi `<12`). OSV 0 temuan, Trivy 0 vulnerability, gate hijau, image sudah di-rebuild | **Critical** | `pyproject.toml`, `uv.lock`, `reports/osv-scanner.json`, `reports/trivy-fs.json` | Selesai — verifikasi ulang saat scan berkala | [x] |
| **E-02** | `python-jose` + `ecdsa` + `rsa` dihapus → `pyjwt[crypto]` 2.15.1; `backend/core/auth.py` memakai `jwt.InvalidTokenError`. OSV 0 temuan, gate hijau, bridge/auth 200, image sudah di-rebuild | **High** | `pyproject.toml`, `uv.lock`, `backend/core/auth.py` | Selesai — awasi warning `InsecureKeyLengthWarning` bila `SECRET_KEY` < 32 byte | [x] |
| **E-03** | `client_secret_2.json` ada di root repo (gitignored) dan **terkonfirmasi ikut ter-copy ke image** (`/app/client_secret_2.json`) karena `COPY . .`. Pemilik memilih file tetap di workspace | **High** | Checkov `CKV_SECRET_6`; inspeksi image API | Ditambahkan ke `.dockerignore` + image di-rebuild. **Rotasi Google OAuth client secret tetap wajib** karena pernah ada di image | [🔶] |
| **E-04** | Image Docker tidak punya `HEALTHCHECK` dan berjalan sebagai root | **Medium** | Checkov `CKV_DOCKER_2`, `CKV_DOCKER_3` pada 3 Dockerfile | `HEALTHCHECK` + user non-root di 3 Dockerfile + `scripts/container_health.py`; container terverifikasi healthy → Checkov Dockerfile **245 passed, 0 failed** (lihat E-15) | [x] |
| **E-05** | Checkov membaca folder internal `uv-tools/`, `reports/`, dan `temp/zap-scan-auth.yaml` sehingga 59 temuan sebagian besar false positive | **Medium** | `reports/checkov.json` | `SKIP_DIRS`/`SKIP_PATTERNS` di `securities/lib/common.py` dipakai Trivy + Checkov; Trivy jadi 6 target/0 secrets, Checkov 0 failed | [x] |
| **E-06** | BetterLeaks melaporkan 13 pola "credential-like" (default DB URL, placeholder `.env.example`, README) | **Low** | `reports/betterleaks.json`; Gitleaks = 0 | Baseline `securities/configs/betterleaks-baseline.json` (13 temuan historis terverifikasi), wrapper pakai `--baseline-path`; rule tetap aktif → **0 findings** | [x] |
| **E-07** | Hadolint `DL3059`: dua `RUN` berturut di `frontend/Dockerfile:13` | **Low** | `reports/hadolint.json` | `bun install` dan `bun --bun run build` digabung dalam satu `RUN` | [x] |
| **E-08** | Nuclei `info`: `/docs`, `/redoc`, `/openapi.json` terekspos; header `COEP`/`COOP` belum ada | **Info** | `reports/nuclei.json` | Tambah COOP/COEP/CORP/HSTS/CSP global di middleware; missing-header hilang (dari 9 → 3 temuan). 3 info docs sengaja dipertahankan karena project lokal pribadi, Swagger/OpenAPI tetap 200 dengan CSP CDN | [x] |
| **E-09** | Checkov/OpenAPI: `global security` kosong dan array tanpa `maxItems` | **Low** | `docs/openapi.json` via `CKV_OPENAPI_4/5/21` | `backend/main.py::_hardened_openapi` menambah global `security` (JWT + opsi anonim) dan `maxItems=500` rekursif; snapshot regenerasi (47 path); Checkov OpenAPI **5 passed, 0 failed** | [x] |
| **E-10** | `pip-audit` untuk `uv.lock` gagal (pip dry-run install error) | **Info** | log background `pip-audit4.err` | Invocation diperbaiki jadi `pip-audit --no-deps --disable-pip -r ... -f json -o ...`, dipakai juga di `security-zap.yml`; hasil **0 known vulnerabilities** | [x] |
| **E-15** | Checkov Dockerfile `CKV_DOCKER_2/3` (healthcheck & USER) dan `CKV_SECRET_4` kredensial hardcode di `docker-compose.yml` | **Medium** | `securities/reports/checkov.json` | `HEALTHCHECK` + user non-root di 3 Dockerfile, `scripts/container_health.py`, `RABBITMQ_URL_INTERNAL` wajib dari `.env`; Checkov **0 failed** semua check type, `docker compose config` valid | [x] |
| **E-11** | `POST /auth/bridge` mengembalikan 404 `User tidak ditemukan` untuk email owner yang ada di `OWNER_EMAILS` tetapi belum punya baris di `users` (mis. `uewfau@gmail.com`). `/auth/google` auto-create, bridge tidak | **High** | log API `POST /auth/bridge 404`; `backend/routes/bridge.py` | Bridge provisioning owner otomatis setelah bridge token + whitelist lolos; diuji `tests/test_bridge.py::test_bridge_provisions_missing_owner` | [x] |
| **E-12** | Better Auth tidak bisa resolve IP klien di container (`NODE_ENV=production`, tanpa reverse proxy) → rate limit jadi bucket global + warning berulang | **Low** | log frontend `Rate limiting could not determine a client IP` | Handler `/api/auth/*` meng-inject `x-forwarded-for` dari `request.ip` srvx (menimpa nilai klien); verifikasi 0 warning + `/api/auth/get-session` 200 | [x] |
| **E-13** | Build context 1,76 GB; `client_secret_2.json` dan `securities/` ikut ter-copy ke image karena `.dockerignore` tidak menutupnya | **High** | log `docker compose up --build`; `/app/client_secret_2.json` di image lama | `.dockerignore` diperluas (`securities/`, `client_secret*.json`, `.agents/`, `.claude/`, `node_modules/`, artefak frontend); context turun ke 89,93 kB; image baru diverifikasi bersih | [x] |\n| **E-14** | `GET /revenue/advice` → 503 `OpenAIModelNotFoundError`: service meng-hardcode OpenRouter + model `:free` yang sudah tidak ada, mengabaikan `AGENT_PROVIDER/AGENT_MODEL` | **Medium** | log API `[RevenueAdvice] invoke gagal`; `backend/services/revenue_advice.py` | Satu jalur LLM `AGENT_*`; `REVENUE_AI_MODEL` opsional (provider/model). Diuji `tests/test_revenue.py` + endpoint runtime | [x] |

Perintah penutup setelah perbaikan:

```powershell
uv run python scripts/gate.py
uv run python securities/run_all.py --include-nuclei --allow-failure
uv run python scripts/zap_auth_scan.py
```

Estimasi Fase D: 2–3 hari kerja. Prioritas: D-05, D-07, D-11 lebih dulu.
Fase E: kerjakan E-01/E-02/E-03 lebih dulu (dependency + credential nyata).

---

**Versi**: 2026-11-25 · **Pemilik**: project pribadi · **Status**: aktif
