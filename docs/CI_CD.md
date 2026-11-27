# CI/CD & Kolaborasi GitHub

> **Scope aplikasi: LOKAL SAJA.** Tidak ada deploy ke server/VPS/cloud. GitHub Actions hanya dipakai
> untuk CI (gate) dan — bila diperlukan — membangun artifact ZIP. Jangan tambahkan langkah deploy.

Panduan untuk workflow GitHub di [`adhitiad/clip-ai`](https://github.com/adhitiad/clip-ai).
Terkait: [`GOAL.md`](GOAL.md) (goal/workflow), [`API.md`](API.md) (kontrak).

## 1. Ringkasan

| File | Fungsi | Pemicu |
| --- | --- | --- |
| `.github/workflows/ci.yml` | **CI**: gate Python (`scripts/gate.py`) + job frontend `bun --bun run test:a11y` (screenshot + axe) | push/PR ke `master`, manual |
| `.github/workflows/security-zap.yml` | **Security**: ZAP terautentikasi (SQLite terisolasi + guard read-only), gagal jika ada alert High/Medium | push/PR ke `master`, manual |
| `.github/workflows/cd.yml` | **CD**: jalankan gate, buat ZIP source, upload artifact + GitHub Release | push tag `v*`, manual |
| `.github/ISSUE_TEMPLATE/` | Bug report, feature request, config (blank issue dimatikan) | saat buka issue |
| `.github/DISCUSSION_TEMPLATE/` | Ideas, Q&A, Show & tell | saat buka discussion |

Tidak ada deploy ke server. Docker lokal tersedia ([`DOCKER.md`](DOCKER.md)). CD hanya memproduksi **artifact source** secara opsional.

## 2. CI — Python gate

`ci.yml` berjalan di `ubuntu-latest` dengan Python **3.14** (sama seperti `.python-version`) dan uv:

```text
checkout → setup-uv (python 3.14, cache) → uv sync --frozen → uv lock --check
         → services.postgres (postgres:19.0-alpine3.24, DB clip_ai, healthcheck)
         → uv run python scripts/gate.py   [GATE_DATABASE_URL → service Postgres]
```

Gate mencakup: `ruff check`, `ruff format --check`, `docs/openapi sync`, `compileall`, PostgreSQL ping (`SELECT 1`), `pytest`, import `backend.main`, import `workers.worker`.
Gate memakai env dummy untuk API key, tetapi **membutuhkan PostgreSQL nyata** lewat `GATE_DATABASE_URL` (service `services.postgres`). RabbitMQ dan API key tidak diperlukan di runner.

Aturan:
- PR yang gagal gate tidak boleh di-merge.
- `concurrency` membatalkan run lama pada ref yang sama.
- Dependensi harus dikunci di `uv.lock`; jangan commit lockfile yang tidak sinkron.

Jalankan lokal sebelum push:

```powershell
uv sync --frozen
uv run python scripts/gate.py
```

### CI — Visual & aksesibilitas frontend

Job `frontend-a11y` berjalan paralel dengan gate Python (Bun 1.4.2, lockfile frontend frozen):

```text
checkout → setup-bun → bun install --frozen-lockfile → bunx playwright install --with-deps chromium
         → bun --bun run test:a11y   [14 rute: screenshot + axe WCAG 2 A/AA]
```

Screenshot tiap rute publik/protected dilampirkan sebagai artifact Playwright; violation `serious`/`critical` menggagalkan job. Job memakai placeholder Better Auth (bukan kredensial nyata) karena test mem-stub session. Jalankan lokal dari `frontend/`:

```powershell
bun --bun run test:a11y
```

### CI — Security scan (OWASP ZAP, tanpa Strix)

`security-zap.yml` menjalankan `scripts/zap_auth_scan.py` dengan `ZAP_DOCKER=1`
(memakai image `ghcr.io/zaproxy/zaproxy:stable`, tidak butuh Java/ZAP terpasang di runner).
Skrip membuat DB SQLite sementara, JWT lewat `/auth/bridge`, OpenAPI terfilter, dan guard
ASGI read-only. Job gagal bila `zap-report-auth.json` mengandung alert **High/Medium**;
laporan di-upload sebagai artifact. Langkah berikutnya menjalankan
`scripts/audit_logs.py` (A09 — memastikan tidak ada secret/JWT di `trace.jsonl`
dan `audit.jsonl`).

Workflow yang sama punya job `sca` (A03): `uv export` → `pip-audit` untuk
`uv.lock`, dan `bun audit --json` untuk `frontend/bun.lock`. Keduanya diringkas
`scripts/audit_dependencies.py`; build gagal jika ada temuan **High/Critical**.

Invocation `pip-audit` yang benar untuk requirements hasil `uv export` adalah
`uvx pip-audit --no-deps --disable-pip -r temp/requirements-audit.txt -f json -o temp/pip-audit.json`.
Tanpa `--no-deps --disable-pip`, pip mencoba resolve dan install sehingga
gagal pada lockfile yang sudah lengkap dengan hash. Hasil terakhir: **0 known
vulnerabilities**.

Jalankan lokal dengan ZAP terpasang:

```powershell
uv run python scripts/zap_auth_scan.py
```

Atau dengan Docker (Linux):

```powershell
$env:ZAP_DOCKER = '1'
uv run python scripts/zap_auth_scan.py
```

## 3. CD — Source artifact

`cd.yml` dipicu oleh tag `v*`:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Alur:

```text
checkout → setup-uv → uv sync --frozen → gate → git archive → dist/clip-ai-v0.1.0-source.zip
         → upload-artifact → gh release create/upload
```

Artifact dibuat dengan `git archive HEAD`, jadi **hanya file ter-commit** yang masuk:
tidak ada `.env`, `.venv/`, `temp/`, `output/`, `models/*.pkl`, `logs/`, atau media.

Izin: `contents: write` (untuk `gh release`). Token memakai `secrets.GITHUB_TOKEN` bawaan GitHub — **tidak perlu secret tambahan**.

Jika release sudah ada, workflow melakukan `gh release upload --clobber` agar artifact diperbarui.

## 4. Issue

Gunakan template yang tersedia:

| Template | Dipakai untuk |
| --- | --- |
| **Bug report** | Error yang bisa direproduksi; wajib langkah reproduksi, versi Python/uv, OS, dan output gate |
| **Feature request** | Usulan fitur; wajib kriteria selesai + centang batasan "tanpa model ML" & "test di `tests/**`" |

`blank_issues_enabled: false` — issue kosong ditolak. Untuk pertanyaan, arahkan ke Discussions lewat `config.yml`.

**Jangan pernah** menempelkan `.env`, API key, JWT, kredensial DB, atau data user ke issue/discussion.

## 5. Discussion

Kategori yang disiapkan:

| Template | Topik |
| --- | --- |
| **Ideas** | Usulan fitur level tinggi, sebelum jadi issue |
| **Q&A** | Cara pakai/konfigurasi (env, provider, render, API) |
| **Show & tell** | Hasil short/reel/tiktok dari agent + catatan perbaikan |

Alur yang disarankan:

```text
Diskusi (ide/pertanyaan) ──disepakati──▶ Issue (feature/bug) ──▶ PR ──▶ CI gate ──▶ merge ──▶ tag v* ──▶ CD
```

## 6. Perubahan dokumen

Sesuai aturan repo, perubahan route/schema/auth/status wajib memperbarui `docs/API.md` **dan** tabel API di `README.md`.
Perubahan workflow/artifact memperbarui file ini. Perubahan perilaku agent memperbarui `docs/GOAL.md`. Perubahan konfigurasi RabbitMQ memperbarui `docs/RABBITMQ.md` dan `.env.example`.

Branch Redis sudah dihapus. Branch CI/CD hanya di `master`.
