# Frontend — Clip AI (TanStack Start)

UI untuk studio short-form pribadi: login Google (Better Auth), halaman protected
(`/`, `/shorts`, `/niche`, `/history`, `/dashboard`, `/tools`, `/backend`,
`/protected`), dan halaman publik (`/landing`, `/login`, `/about`, `/tos`,
`/privacy`, `/contact`).

Arah visual: **shonen neon gelap**. Palet, tipografi, dan dial ada di
[`DESIGN.md`](DESIGN.md). Semua data berasal dari backend; frontend tidak
mengarang angka, status, atau daftar provider.

## Menjalankan

Dari folder `frontend/`, satu-satunya package manager adalah **bun/bunx**:

```powershell
bun install
bun --bun run dev        # http://localhost:3000
```

Jangan pakai npm/pnpm/yarn untuk frontend.

## Gate

Jalankan dari `frontend/`:

```powershell
bun --bun run typecheck   # tsc --noEmit
bun --bun run lint        # eslint src
bun --bun run check       # prettier --check .
bun --bun run test        # vitest
bun --bun run test:e2e    # playwright (51 test)
bun --bun run test:a11y   # playwright --grep @a11y (14 test)
bun --bun run build       # vite build (produksi)
```

Semua gate harus hijau sebelum selesai. `routeTree.gen.ts` dan `src/paraglide/`
adalah generated; regenerasi dengan `bun --bun run generate-routes` atau dev/build.

## Struktur

| Path                             | Peran                                                                              |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| `src/routes/_protected/`         | Delapan halaman login-required (layout `_protected.tsx`)                           |
| `src/routes/api/youtube/`        | Server routes: OAuth start/callback + scheduler trigger                            |
| `src/routes/api/auth/$.ts`       | Handler Better Auth + injeksi IP klien                                             |
| `src/components/app-shell.tsx`   | Sidebar, navbar, bottom nav, wordmark (semua rute terdaftar)                       |
| `src/components/public-page.tsx` | `PublicNav` + `PublicFooter` untuk semua halaman publik                            |
| `src/lib/queries.ts`             | TanStack Query, termasuk `opsAccessLogQuery`                                       |
| `src/lib/shorts-api.ts`          | Server fn `createShorts`: brief, render, auto-discover, fallback RabbitMQ → Taskiq |
| `src/server/queue.ts`            | Producer/konsumen RabbitMQ `shorts-render` + kirim payload ke `render_job.py`      |
| `src/server/telemetry.ts`        | `traceparent` W3C untuk server fn & worker AMQP                                    |
| `src/validation/api.ts`          | Daftar path API yang diizinkan (`API_PATHS`)                                       |
| `src/styles.css`                 | Token shonen neon gelap + Utility komponen                                         |

## Alur data

- Backend JWT dibuat server-side lewat `POST /auth/bridge` (`AUTH_BRIDGE_TOKEN`),
  tidak pernah diekspos ke klien.
- `createShorts` memanggil `POST /agent/shorts`. Tanpa URL dan dengan
  `auto_discover=true`, backend mencari 2-10 video dari topik lalu merender satu
  MP4 mix. Satu URL tetap lewat RabbitMQ; multi-URL/auto-discover lewat Taskiq.
- Thumbnail klip disajikan backend lewat `GET /download/thumbnails/*.jpg`.
- Access log (jika `MONGODB_URL` diset) tampil di panel
  **Access Log (MongoDB)** pada halaman `/backend`.

## Environment

`frontend/.env.local` berisi `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`AUTH_BRIDGE_TOKEN`, `BETTER_AUTH_SECRET`, `SERVER_URL`, `RABBITMQ_URL`, dan
`YOUTUBE_OAUTH_*` + `YOUTUBE_TOKEN_ENCRYPTION_KEY`. Jangan commit file ini.

Untuk menjalankan Playwright terhadap dev server lokal (bukan container yang
mungkin masih memakai build lama), set `E2E_BASE_URL`, misalnya
`$env:E2E_BASE_URL='http://localhost:3100'` sebelum `test:e2e`/`test:a11y`.

## Catatan

- Intent skill: `bunx --no-install --package @tanstack/intent intent list`.
- `frontend/anti-slop/` berisi laporan Delivery Gate untuk audit UI.
- Semua ikon memakai **lucide-react**, bukan aset SVG.
