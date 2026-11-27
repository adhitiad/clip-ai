# API Contract — Clip AI (Project Pribadi)

Base URL: `http://127.0.0.1:8000` (lokal) atau `http://localhost:8000` (host Docker). OpenAPI interaktif: `/docs`, schema: `/openapi.json`.

Snapshot OpenAPI yang di-commit: [`docs/openapi.json`](openapi.json) (dari `app.openapi()`, **47 path**, judul `Clip AI API` v0.1.0). Semua endpoint `dashboard`, `tools`, dan `ops` kini punya `response_model` dengan skema lengkap. Sebagian endpoint lama di `agent`, `clips`, `niche`, `tasks`, dan `youtube` masih mengembalikan dict bebas sehingga skema `200`-nya `{}` — detail response ada di halaman ini.

Route statis `GET /download/*` (thumbnail/video hasil auto-discover) tidak masuk OpenAPI karena di-mount lewat `StaticFiles`, bukan router. Hanya melayani file di folder `download/` (gitignored & dockerignored).

## Autentikasi

- Login: `POST /auth/google` dengan `{id_token}` (Google ID token dari frontend Better Auth) → `200 {access_token, token_type}` (`Token`).
- Profil: `GET /auth/me` → `200 {email, username}` (`UserOut`).
- Hanya email di `OWNER_EMAILS` yang diizinkan.
- Kirim `Authorization: Bearer <token>` untuk semua endpoint.
- **Tidak ada password, role, plan, kredit, atau billing.**
- Error: `400` validasi, `401` token invalid, `403` email tidak diizinkan, `404` tidak ditemukan, `422` body/query invalid, `429` rate limit AI, `502` gagal panggil AI eksternal, `503` env/kredensial belum diset.

## Health

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| GET | `/health/live` | publik | `200 {status:"ok"}`, dipakai Docker healthcheck |
| GET | `/health/ready` | publik | `200 {status:"ready", database:true, broker:{...}}`; `503` bila DB atau broker mati |

## Auth

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| POST | `/auth/google` | publik | `id_token`, `referral_code?` — daftar/login otomatis → `{access_token, token_type}` |
| GET | `/auth/me` | login | profil user → `{email, username}` |

## Clips

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| POST | `/clips/generate-clips` | login | `url`, `user_query`, `target_language` → antre render Taskiq. Response: `200 {status:"processing", message, task_id, request_id, hooks_found, data:[...]}` |
| POST | `/clips/feedback` | login | `clip_id`, `score` (+1/-1). Response: `200 {status, message}` |
| GET | `/clips` | login | Daftar clip (`limit`, `offset`) |
| GET | `/clips/{clip_id}` | login | Detail clip |
| PATCH | `/clips/{clip_id}` | login | Update `title_en`, `desc_en`, `score` |
| DELETE | `/clips/{clip_id}` | login | Hapus clip |

## Shorts Agent

| Method | Path | Akses | Body / catatan |
| --- | --- | --- | --- |
| POST | `/agent/shorts` | login | `topic` (wajib), `video_url?` / `video_urls[]` (maks 5), `platform` (`shorts`/`reels`/`tiktok`), `target_language`, `max_clips`, `render_video`, `auto_discover` (default `true`), `mix_sources` (default `true`), `min_source_seconds` (default `240`), `provider?`, `model?` |

- `render_video=false` → `200 {status:"brief", brief: ShortsPlan}` (hook, judul, caption, hashtag).
- `render_video=true` → jika `video_urls` kosong dan `auto_discover=true`, AI otomatis mencari 2-10 video (>4 menit) dari YouTube + Exa/Tavily/Firecrawl/Selenium yang relevan topik, lalu mix jadi satu MP4. Satu URL → MP4 per klip; lebih dari satu URL → **satu MP4 hasil gabungan** klip dari tiap sumber. Tanpa topik dan tanpa URL → `422`.
- Hasil `200 {status:"processing", task_id, request_id, queue, brief, queued_clips, mix_sources, sources, thumbnails}`. `queue`: `rabbitmq` (satu sumber) atau `taskiq` (mix multi-sumber / fallback). Worker menghasilkan MP4 9:16.
- Response brief: `{platform, topic, clips: [{start_time, end_time, hook, title, caption, hashtags, thumbnail_path?, thumbnail_url?}], style_notes}`.
- Response render: `{status, task_id, request_id, brief, queued_clips, mix_sources, sources, thumbnails: [url...]}`. Setiap klip punya thumbnail di `GET /download/thumbnails/<file>.jpg`.
- Penemuan video otomatis memakai `backend/services/video_discovery.py` (YouTube yt-dlp + Exa/Tavily/Firecrawl/Selenium-BeautifulSoup, AI seleksi lewat AGENT_PROVIDER/AGENT_MODEL). Tanpa topik (`topic`) tidak bisa menjalankan auto-discover.
- Provider LLM via `AGENT_PROVIDER`/`AGENT_MODEL` atau argumen; default `nvidia`/`nvidia/nemotron-3.5-super-vl-120b-a12b`.
- Job render membawa intelegensi konten: analisis video (STT+LLM), brief, `trend_terms`, dan skor viral rule-based — lihat [`docs/RABBITMQ.md`](RABBITMQ.md).

## Niche & Discovery

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| GET | `/niche/trending` | login | `geo`, `max_items` (5–50) |
| GET | `/niche/suggest` | login | `geo`, `max_trends` (10–50) |
| GET | `/niche/find-videos` | login | `query`, `max_results`, batas durasi |
| GET | `/niche/search-web` | login | `query`, `num_results`, `search_type` |
| POST | `/niche/analyze-and-queue` | login | pipeline lengkap trending → AI → antre render |

`search_type`: `auto`, `fast`, `deep-lite`, `deep`, `deep-reasoning`, `instant`.

## AI Tools

| Method | Path | Akses | Body / catatan |
| --- | --- | --- | --- |
| POST | `/tools/dub` | login | `video_path` (dalam `DUB_ALLOWED_ROOT`), `target_lang`, `keep_original_audio`, `output_path?`, `script_text?` → `200 {status, dubbed_video, target_language, original_video, message}` |
| POST | `/tools/viral-score` | login | `title`, `description`, `start_time`, `end_time`, `has_broll`, `audio_path`, `threshold` → `200 {status, title, viral_score, should_render, confidence_mode, threshold, features{...10}, recommendation}` |
| GET | `/tools/providers` | login | katalog provider/model dari backend, sumber tunggal daftar frontend. Response: `200 {status, providers: [{id, kind, free, models, latency_hint, cost_tier, healthy}], tts, stt}` |
| GET | `/tools/platforms` | login | daftar platform shorts dari backend, sumber tunggal pilihan frontend. Response: `200 {status, platforms: string[], default}` |
| GET | `/tools/model-status` | login | status scoring rule-based (`enabled: false`). Response: `200 {status, model: {trained, enabled, confidence_mode}, message}` |
| GET | `/tools/calibration` | login | korelasi skor prediksi vs feedback nyata: `200 {status, samples, correlation, mean_predicted, mean_actual, buckets, note}` |
| POST | `/tools/feedback` | login | `clip_id`, `actual_views`, `actual_likes`, `actual_shares` → `200 {status, clip_id, message}` |

### Response `POST /tools/viral-score`

```json
{
  "status": "success",
  "title": "...",
  "viral_score": 7.2,
  "should_render": true,
  "confidence_mode": "rule_based",
  "threshold": 6.5,
  "features": {
    "duration_score": 0.5,
    "title_power_words": 2,
    "desc_power_words": 1,
    "title_length_score": 0.8,
    "has_broll": true,
    "audio_energy": 0.4,
    "audio_pitch": 0.3,
    "face_emotion": 0.6,
    "face_count_norm": 0.7,
    "hook_ratio": 0.9
  },
  "recommendation": "RENDER — konten ini berpotensi viral!"
}
```

`recommendation`: `RENDER — konten ini berpotensi viral!` atau `SKIP — skor <threshold> <threshold>`.

## Dashboard

| Method | Path | Akses |
| --- | --- | --- |
| GET | `/dashboard/overview` | login |
| GET | `/dashboard/history` | login (`page`, `page_size`, `search`, `sort_by=id\|title\|score`, `sort_dir=asc\|desc`) | response `200 {status, page, page_size, total, search, sort_by, sort_dir, items}` |
| GET | `/dashboard/profile` | login | `200 {status, id, email, username, joined_at}` |
| GET | `/dashboard/stats` | login | `200 {status, daily, total, peak}` (7 hari terakhir) |
| GET | `/dashboard/health` | login | `200 {status, health: {database: {ok}, rabbitmq: {ok}}}` |

## Revenue (pendapatan platform, read-only)

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| GET | `/revenue/summary` | login | Ringkasan pendapatan YouTube/TikTok/Meta Reels (`days=7..365`, default 28) |
| GET | `/revenue/advice` | login | Saran peningkatan pendapatan via model teks `AGENT_*` (atau override `REVENUE_AI_MODEL`); `429` rate limit, `502` gagal AI, `503` model/API key belum siap |

Response:

- `GET /revenue/summary` → `200 {status, days, platforms: [{platform, available, status, amount, currency, period_start, period_end, source, note}], total_available, currency, generated_at, note}`. Platform tanpa API/scope ditandai `available:false` dan **tidak** dihitung sebagai nol.
- `GET /revenue/advice` → `200 {status, provider, model, recommendations: string[], generated_at, note}`. `provider`/`model` mengikuti `AGENT_PROVIDER`/`AGENT_MODEL` atau `REVENUE_AI_MODEL`. Saran AI, bukan jaminan pendapatan.

Sumber data:

- YouTube: YouTube Analytics v2 `estimatedRevenue` (`channel==MINE`) memakai token OAuth terenkripsi dari `frontend/.data/youtube_tokens.json`. Perlu scope `yt-analytics-monetary.readonly` (ulangi OAuth bila token lama) dan channel yang eligibel.
- TikTok / Meta Reels: API publik tidak mengekspos pendapatan creator. Adapter disiapkan (`backend/services/platform_revenue.py`) dan sengaja dikembalikan `available:false`.

Modul ini **bukan** billing: tidak ada saldo, pembayaran, atau bookkeeping.

## Tasks

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| GET | `/tasks/{task_id}` | login | Status task Taskiq: `{task_id, status, progress, error, attempts}` (`status`: `PENDING` / `PROGRESS` / `STARTED` / `SUCCESS` / `FAILURE`; `progress`: `{current, total, percent}` saat `PROGRESS`, otherwise `null`; `attempts`: percobaan ke-N) |

Dipakai UI `/shorts` untuk polling render baik dari worker RabbitMQ maupun fallback Taskiq; status diambil dari `task_results` (PostgreSQL + cache). `progress` berisi `{current,total,percent}` saat status `PROGRESS`.

## Operations & Settings

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| GET | `/ops/tasks` | login | daftar task (`limit`, `status`) dari `task_results` |
| DELETE | `/ops/tasks/{task_id}` | login | hapus hasil task + cache |
| GET | `/ops/queue` | login | health broker RabbitMQ + jumlah task per status |
| GET | `/ops/cache` | login | daftar entri cache render (`output/manifest.json`) |
| POST | `/ops/cache/invalidate` | login | `{cache_key?}` atau `{all:true}` |
| GET | `/ops/traces` | login | tail `logs/trace.jsonl` (`limit`) |
| GET | `/ops/workers` | login | deteksi inti fisik & jumlah worker (`TASKIQ_WORKERS` override) |
| GET | `/ops/export` | login | ekspor clip/feedback/task/pengaturan → JSON |
| DELETE | `/ops/data` | login | hapus semua data pribadi, butuh `{confirm:"DELETE"}` |
| GET | `/ops/audit` | login | tail `logs/audit.jsonl` (panggilan LLM/TTS/STT) |
| GET | `/ops/access-log` | login | identitas per-request dari MongoDB: IP, email, device, browser, HTTP version, flag (`?limit`, `?only_flagged=true`) |
| GET | `/ops/health` | login | snapshot versi, uptime, DB, broker, task, DLQ, worker, provider health, dan status embedding |
| POST | `/ops/render` | login | enqueue render Taskiq manual: `{video_url, clips, lang}` |
| GET | `/settings/me` | login | pengaturan user (dibuat otomatis bila belum ada) |
| PATCH | `/settings/me` | login | update profil & preferensi |
| GET | `/settings/owner` | login | pengaturan owner pribadi |
| PATCH | `/settings/owner` | login | update monitoring & notifikasi |

### Respons endpoint baru

- `GET /ops/tasks` → `200 [{task_id, status, progress, result, error, attempts}]`.
- `GET /ops/queue` → `200 {broker: {ok, provider, version, error}, counts: {PENDING|PROGRESS|SUCCESS|FAILURE: jumlah}, dead_letter_queue: "shorts-render-dlq", retry_policy: {max_retries: 2, delay_seconds: 3, jitter: true}}`.
- `GET /ops/cache` → `200 [{cache_key, files, created_at}]`; `POST /ops/cache/invalidate` → `200 {status, removed}`.
- `GET /ops/traces` → `200 [{event, timestamp, trace_id, request_id}]` (tanpa API key/JWT).
- `GET /ops/workers` → `200 {physical_cores, recommended_workers, configured_workers}`; `recommended_workers` minimal 1 (genap untuk 2+ core), `configured_workers` = 0 bila `TASKIQ_WORKERS` kosong.
- `POST /ops/render` → `200 {status:"processing", task_id, queued_at}`.
- `GET /ops/export` → `200 {status, generated_at, version, clips, feedback, task_results, settings}`.
- `DELETE /ops/data` → `200 {status, deleted: {tabel: jumlah}}`; `400` bila konfirmasi bukan `"DELETE"`.
- `GET /ops/audit` → `200 [{timestamp, kind, provider, model, success, request_id, trace_id, span_id}]`.
- `GET /ops/access-log` → `200 [{timestamp, level, actor, flag, ip, email, user_type, device_id, device_name, browser, http_version, method, path, status, keterangan, line}]`. Klasifikasi: `user ✅` (JWT/OWNER_EMAILS), `** ⚠️` (anonim), `hacker ❌` (IP asing + auth gagal / UA mencurigakan), `error 🛑` (status ≥500). Format baris: `level - actor - tgl jam - keterangan - flag`. MongoDB via `MONGODB_URL`; kosong → `[]`. Tidak menyimpan token/JWT (hash 8 char untuk korelasi).
- `GET /ops/health` → `200 {status, version, uptime_seconds, database, broker, tasks, dlq, workers, providers, embeddings}`.
- `GET`/`PATCH /settings/me` → `200 {id, user_id, display_name, bio, avatar_url, preferred_language, timezone, email_notifications}`.
- `GET`/`PATCH /settings/owner` → `200 {id, owner_user_id, monitor_enabled, monitor_refresh_seconds, alert_queue_threshold, notify_email}`.
- `GET`/`PATCH /clips/{clip_id}` → `200 {id, video_url, topic, start_time, end_time, title_en, desc_en, score, user_id}`; `DELETE` → `200 {status, clip_id}`.

## YouTube Research & Scheduler

| Method | Path | Akses | Catatan |
| --- | --- | --- | --- |
| POST | `/youtube/search` | login | YouTube Data API v3 (`YOUTUBE_DATA_API_KEY`) |
| GET | `/youtube/scheduler/status` | login + `X-Cron-Secret` | health scheduler |
| POST | `/youtube/scheduler/collect` | login + `X-Cron-Secret` | kumpulkan kandidat video |

Frontend (server routes): `POST /api/youtube/scheduler` (placeholder trigger, `X-Cron-Secret` — endpoint backend nyata ada di `/youtube/scheduler/status` dan `/collect`), `GET /api/youtube/oauth/start` (redirect consent Google), `GET /api/youtube/oauth/callback` (tukar `code` → token, tersimpan terenkripsi via `YOUTUBE_TOKEN_ENCRYPTION_KEY`, T-19).

## Perubahan kontrak

Setiap perubahan path/schema/auth/status code wajib memperbarui file ini **dan** tabel API di `README.md`, `backend/README.md`, serta `docs/PERSONAL.md`. Perubahan metadata aplikasi (judul/versi) juga wajib di-regenerate ke `docs/openapi.json`.
