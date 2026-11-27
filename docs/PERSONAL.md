# Project Pribadi — Clip AI

Mode operasi: **satu user (pemilik), tanpa role, plan, kredit, atau billing**.

## 1. Akses

- Login **Google-only** via `POST /auth/google` dengan Google ID token.
- Frontend Better Auth: secret kuat, `trustedOrigins`, rate limit aktif, cookie cache `jwe`, OAuth token terenkripsi, CSRF tidak dimatikan.
- Email yang diizinkan berasal dari `OWNER_EMAILS` di `.env` (disalin dari project `aivisio`).
- Semua endpoint lain memakai Bearer JWT dari endpoint tersebut.
- Tidak ada `/auth/token`, `/auth/register`, `/auth/bootstrap-owner`, `/auth/set-role`.
- Tidak ada password. Kolom `hashed_password` berisi sentinel `GOOGLE_OAUTH`.

## 2. Yang dihapus

| Fitur | Status |
| --- | --- |
| `UserRole` (OWNER/STAFF/USER) | Dihapus |
| `UserPlan` (FREE/PREMIUM/BUSINESS/ENTERPRISE) | Dihapus |
| Kredit (`credits`, `used_credits`) | Dihapus |
| `require_role`, `require_plan`, `check_credits`, consume/refund | Dihapus |
| `/billing/*` | Dihapus |
| `/dashboard/owner/*`, `/dashboard/godsmode/*`, `/dashboard/user-growth` | Dihapus |
| Seed 6 user demo | Diganti 1 user dari `OWNER_EMAILS` |

`require_owner` tetap ada sebagai alias sederhana (semua user login = pemilik).

## 3. Yang tersisa

- Shorts agent: `POST /agent/shorts` **(brief/render)** + UI `/shorts` (form, provider ber-icon); beberapa URL video (>4 menit) di-mix jadi satu short
- Klip: `POST /clips/generate-clips`, `POST /clips/feedback`
- Niche: trending, suggest, find-videos, search-web, analyze-and-queue
- Tools: dub, viral-score, providers, platforms, model-status, **calibration**, feedback
- Dashboard pribadi: `/overview`, `/history`, `/profile`, `/stats`, `/health`
- Revenue (read-only): `/revenue/summary`, `/revenue/advice` (model teks `AGENT_*`, bukan billing)
- Tasks: `GET /tasks/{task_id}` (polling render)
- Operations: `/ops/tasks`, `/ops/queue`, `/ops/cache`, `/ops/traces`, `/ops/workers`, `/ops/render`, `/ops/export`, `/ops/data`, `/ops/audit`
- Settings: `GET|PATCH /settings/me`, `GET|PATCH /settings/owner`
- YouTube riset & scheduler: `/youtube/*`
- Stack Docker: `docker compose up -d --build` (db, rabbitmq, api, worker, render-worker, frontend).
- `render-worker` mengonsumsi antrean utama `shorts-render`; `worker` adalah fallback Taskiq. `TASKIQ_WORKERS=6` mengikuti inti fisik mesin.
- Health publik: `/health/live` dan `/health/ready`. Detail owner: `/ops/health`.

## 5. Halaman frontend

- Publik: `/landing` (penjelasan produk), `/login` (Google via Better Auth), `/about`, `/tos`, `/privacy`, `/contact`.
- `frontend/public/robots.txt` mengizinkan halaman publik dan melarang rute protected serta `/api/`. `frontend/public/sitemap.xml` hanya berisi halaman publik. Domain masih localhost dan harus diganti saat deploy.
- Protected: `/` (home lama), `/shorts`, `/niche`, `/history`, `/dashboard`, `/tools`, `/backend`, dan `/protected` (ruang kerja).
- Rute protected berada di layout `_protected` dan redirect ke `/login` bila session Better Auth tidak ada.
- Backend JWT tetap dibuat server-side lewat `POST /auth/bridge`; tidak pernah diekspos ke klien.

## 4. Database

- Model `User`: `id`, `email`, `username`, `hashed_password` (sentinel), `google_sub`, referral.
- Migrasi `0003_personal` menghapus kolom role/plan/credits/used_credits dan enum `userrole`/`userplan`.
- Seed satu user: `uv run python -m backend.scripts.seed_db --reset`.

## 5. Env

```dotenv
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
AUTH_BRIDGE_TOKEN=...   # server-only, frontend + backend harus sama
OWNER_EMAILS=email1@gmail.com,email2@gmail.com
```

Frontend `frontend/.env.local` memakai `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
untuk Better Auth Google provider (tanpa email/password).

## 6. Observability

Setiap respons API punya header `X-Request-ID` (UUIDv7). ID diteruskan ke task Taskiq
sehingga log API dan worker bisa dicocokkan (`req=<id>`).

## 7. Verifikasi

```powershell
uv run python scripts/gate.py
uv run alembic upgrade head
uv run python -m backend.scripts.seed_db --reset
```
