# Security Scan — OWASP ZAP (lokal)

Tool: **OWASP ZAP 2.17.0** di `C:\Program Files\ZAP\Zed Attack Proxy` (bukan Strix).
Target: `http://127.0.0.1:8000` (FastAPI lokal, project sendiri).
Tanggal: 2026-11-24.

## Cara menjalankan

Plan automation: [`zap-scan.yaml`](../zap-scan.yaml) untuk scan anonymous dan `scripts/zap_auth_scan.py` untuk scan dengan login. Script login memakai env: `SECRET_KEY`, `OWNER_EMAILS`, `AUTH_BRIDGE_TOKEN`, dan opsional `ZAP_JAR`, `ZAP_SCAN_PORT`. Semua sudah ada di `.env` / `.env.example`.

```powershell
cd 'C:\Program Files\ZAP\Zed Attack Proxy'
java -Xmx1g -jar zap-2.17.0.jar -cmd -autorun 'E:\code\clip-ai\zap-scan.yaml'
```

Laporan:
- `zap-report.md` — ringkasan eksekutif
- `zap-report.json` — detail alert (mesin-baca)

## Hasil scan

| Metrik | Nilai |
| --- | --- |
| URL dari OpenAPI | 28 |
| URL ditemukan spider | 41 |
| Endpoint aktif discan | 52 |
| Durasi active scan | ~54 detik |
| **High** | **0** |
| **Medium** | **0** |
| **Low** | 1 (ZAP internal warning) |
| Info | 0 |

### Temuan & perbaikan

| Alert | Severity | Status |
| --- | --- | --- |
| X-Content-Type-Options Header Missing | Low | ✅ Diperbaiki — middleware `security_headers` di `backend/main.py` |
| Content-Security-Policy Header Not Set (quick scan `/docs`) | Medium | ✅ Diperbaiki — CSP untuk `/docs`, `/redoc`, `/openapi.json` |
| Missing Anti-clickjacking Header | Medium | ✅ Diperbaiki — `X-Frame-Options: DENY` |
| Sub Resource Integrity / Cross-Domain JS (quick scan `/docs`) | Medium/Low | Dari CDN Swagger UI; diminimalisir lewat CSP |

Header yang ditambahkan:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: (khusus /docs, /redoc, /openapi.json)
```

## Catatan cakupan (jujur)

- Semua endpoint butuh Google JWT, sehingga **scan berjalan sebagai anonymous** — sebagian besar respons 401/422. Ini menguji lapisan auth & error handling, bukan otorisasi data setelah login.
- OWASP Top 10:2025: ZAP kuat di A02 (misconfig), A05 (injection), A07 (auth), A10 (error handling). **A09 (logging & alerting) tidak bisa diuji dari luar.**
- Untuk pengujian setelah login, ZAP bisa dikonfigurasi dengan context + authentication; belum dilakukan karena butuh token Google aktif.

## Re-scan (setelah security headers + endpoint `/tasks`)

Tanggal: 2026-11-24. Target: `http://127.0.0.1:8001` menjalankan **uvicorn lokal dengan kode terbaru** — kontainer di port 8000 masih versi lama (27 path, belum ada `/tasks`) dan Docker dijalankan pemilik repo, jadi tidak di-rebuild di sini. Plan: `zap-scan.yaml` sudah diperbarui untuk memasukkan `tasks` pada `includePaths`.

| Metrik | Sebelum | Sesudah |
| --- | --- | --- |
| URL dari OpenAPI | 28 | 29 (termasuk `/tasks/{task_id}`) |
| URL ditemukan spider | 41 | 43 |
| Endpoint aktif discan | 52 | 54 |
| Durasi active scan | ~54 detik | ~1 menit 24 detik |
| High | 0 | **0** |
| Medium | 0 | **0** |
| Low | 1 (`X-Content-Type-Options` pada 3 respons) | **0** |
| Info alert | 0 | **0** |

Temuan lama `X-Content-Type-Options Header Missing` **hilang** — middleware `security_headers` di `backend/main.py` terbukti efektif. Tidak ada alert baru dari endpoint `/tasks/{task_id}`.

Catatan jujur: laporan mencatat 437 ZAP *warnings* (terutama spider getting 404 pada `/`) dan 92% respons 4xx karena endpoint butuh JWT — keduanya **bukan temuan kerentanan**. Exit code CLI ZAP = 2 karena warning (`failOnWarning: false`); kedua file laporan tetap berhasil dibuat.

## Scan terautentikasi (login) — 2026-11-25

Target: `http://127.0.0.1:8011`, instance **SQLite terisolasi** (`temp/zap_scan.db`) — database asli tidak disentuh. Login memakai `POST /auth/bridge` (owner email + `AUTH_BRIDGE_TOKEN`, bukan password Google). Token disuntikkan ZAP lewat replacer `req_header Authorization`.

```powershell
uv run python scripts/zap_auth_scan.py
```

Skrip membuat spec OpenAPI terfilter (hanya GET read-only), plan ZAP, lalu menjalankan scan. Guard ASGI `scripts/zap_safe_app.py` menolak semua non-GET (kecuali bridge) dan path di luar allowlist — jadi endpoint AI/render/hapus tidak pernah tercapai meski ZAP memfuzz path.

| Metrik | Nilai |
| --- | --- |
| URL diimpor dari OpenAPI terfilter | 23 |
| Durasi active scan | ~9 detik |
| Request mencapai backend | 2.044 |
| Respons 200 | 479 |
| 422 (fuzz parameter) / 404 / 307 | 1.466 / 89 / 8 |
| 401 anonim (sanity) | 2 |
| 500 | **0** |
| Request diblokir guard | 262 |
| **High / Medium / Low / Info** | **0 / 0 / 0 / 0** |

### Temuan nyata yang diperbaiki

`GET /ops/audit` mengembalikan **500** saat `logs/audit.jsonl` berisi record: model respons memakai field `event` yang tidak pernah ditulis `log_ai_call` (record berisi `kind`, `provider`, `model`, ...). Diperbaiki di `backend/routes/ops.py` (`AuditOut` + `span_id`) dan ditambah test `tests/test_lifecycle.py::test_audit_endpoint_maps_records`.

### Catatan cakupan (jujur)

- Percobaan pertama hanya memakai `includePaths` ZAP; filter itu **tidak menahan** OpenAPI import sehingga sempat menyentuh endpoint mahal (`/niche/*`, `/clips/generate-clips`). Karena itu sekarang ada **dua lapis**: spec OpenAPI terfilter + guard ASGI. Pada run final, 262 request berbahaya diblokir sebelum mencapai app.
- Scan ini sengaja hanya GET read-only; POST/PATCH/DELETE tidak diuji (isolasi mencegah efek samping). `/docs` Swagger juga tidak ikut scan login — temuan CSP/SRI di `/docs` sudah dicatat di scan anonymous dan bersifat dev-only.
- Endpoint yang butuh data nyata (mis. `/clips/{id}`) diuji dengan DB kosong; otorisasi per-ID tetap tertutup karena project hanya punya satu user.

## Verifikasi ulang

Setelah perbaikan header, jalankan ulang plan yang sama dan pastikan alert related header hilang.
Bandingkan `zap-report.json` sebelum/sesudah. **Sudah dilakukan**: alert header hilang, 0 alert tersisa (tabel di atas).

### Re-run terautentikasi 2026-11-25 (setelah seluruh perubahan kode)

```powershell
uv run python scripts/zap_auth_scan.py
```

Hasil: **High / Medium / Low / Info = 0 / 0 / 0 / 0**. 23 URL dari OpenAPI terfilter, active scan ~9 detik, 2.044 request (479 `200`, 1.466 `422`, 89 `404`, 8 `307`, 2 `401` anonim, **0 `500`**), 262 request diblokir guard read-only.

Perbaikan tambahan: `scripts/zap_auth_scan.py` kini men-redaksi JWT sebelum mencetak stdout ZAP (`Bearer ***`), karena ZAP automation mencetak nilai `replacer` secara default. Token tetap hanya ada di plan sementara `temp/zap-scan-auth.yaml` (gitignored).

Route `GET /download/*` (static files thumbnail/video) hanya melayani file dari
folder `download/` (gitignored & dockerignored) lewat FastAPI `StaticFiles`;
tidak ada path traversal, tidak ada autentikasi, dan tidak termasuk ke spec
OpenAPI yang di-scan ZAP. Tidak menambah alert baru.

## CI — ZAP saja (tanpa Strix)

Workflow `.github/workflows/security-zap.yml` berjalan pada push/PR ke `master`.
Memakai `ZAP_DOCKER=1` sehingga runner tidak perlu Java/ZAP lokal; image
`ghcr.io/zaproxy/zaproxy:stable` dijalankan dengan `--network host` agar bisa
mencapai uvicorn di `127.0.0.1:8011` yang dibuat skrip. Job gagal jika ada alert
**High/Medium**, dan laporan `zap-report-auth.md` / `.json` di-upload sebagai artifact.
Tidak ada langkah, secret, atau ketergantungan Strix.

## Cakupan OWASP Top 10:2025 dengan ZAP

Edisi yang dipakai: **OWASP Top 10:2025**. Sumber bukti: scan anonymous
(`zap-scan.yaml`) + scan terautentikasi (`scripts/zap_auth_scan.py`), keduanya
menghasilkan **0 alert**. Itu **bukan** berarti kesepuluh kategori "bersih" —
ZAP bukan agen eksploitasi category-by-category, jadi cakupannya jujur sebagai berikut:

| Kategori 2025 | Cakupan ZAP | Bukti / batas |
| --- | --- | --- |
| **A01 Broken Access Control** (termasuk SSRF) | **Parsial** | Anonymous `401`, JWT bridge wajib, path traversal `422`. BOLA/IDOR tidak bisa dibuktikan karena project **satu user** (tidak ada akun kedua/tenant lain). SSRF tidak diuji karena plan hanya GET read-only. |
| **A02 Security Misconfiguration** | **Kuat** | Security headers, CSP `/docs`, 0 alert misconfig; RabbitMQ user non-`guest`, UI `15672` hanya `127.0.0.1`. |
| **A03 Software Supply Chain Failures** | **Tidak tercakup runtime** | ZAP hanya fingerprint versi bila ada. Perlu SCA terhadap `uv.lock` / `frontend/bun.lock` dan review build-provenance. |
| **A04 Cryptographic Failures** | **Parsial** | Tidak ada secret/JWT bocor di response (0 alert); token di-redaksi di log. Transport HTTPS dan enkripsi at-rest perlu review infra/source. |
| **A05 Injection** | **Kuat dalam scope read-only** | Fuzz parameter menghasilkan `422`, tanpa alert SQL/command injection. Endpoint POST/PATCH/DELETE sengaja tidak di-scan oleh guard; perlu scan terpisah untuk itu. |
| **A06 Insecure Design** | **Parsial** | Business-logic abuse butuh threat modelling manusia; project personal mode menyederhanakan model otorisasi. |
| **A07 Authentication Failures** | **Parsial–Kuat** | `401` anonim, `200` dengan Bearer, rate limit `429`. OAuth Google nyata belum lolos dari browser otomatis (UAT-01/02), jadi sesi/token end-to-end belum tervalidasi penuh. |
| **A08 Software/Data Integrity Failures** | **Parsial** | Tidak ada path deserialisasi/update unsigned yang reachable dari scan. Trust boundary CI/CD tidak bisa diuji runtime. |
| **A09 Security Logging & Alerting Failures** | **Tidak bisa dari luar** | Perlu review `logs/trace.jsonl`, `logs/audit.jsonl`, rotasi, dan redaksi secret (sudah ada di D-10). ZAP tidak bisa menilai ini. |
| **A10 Mishandling of Exceptional Conditions** | **Parsial** | `0` respons `500` pada 2.044 request, `422` untuk input buruk, 262 request diblokir guard. Error path internal yang dalam tetap perlu review source. |

Ringkasan: ZAP memberi bukti kuat untuk **A02**, **A05**, dan sebagian **A07/A10**;
**A09 tidak dapat diuji dari luar**; **A01/A03/A04/A06/A08** hanya parsial atau
butuh alat/proses lain. Jangan melaporkan ini sebagai "lolos OWASP Top 10 penuh".

## Cakupan OWASP API Security Top 10:2023 dengan ZAP

Ini taxonomy **API**, berbeda dengan Web Top 10:2025 di atas. Sumber bukti tetap
dua scan ZAP yang sama (anonymous + terautentikasi read-only), **0 alert**.
Edision yang dipakai: **API Security Top 10:2023**.

| Kategori API 2023 | Cakupan ZAP | Bukti / batas |
| --- | --- | --- |
| **API1 Broken Object Level Authorization (BOLA)** | **Tidak lengkap** | Butuh dua akun/tenant untuk membuktikan akses lintas objek. Project **satu user** (Google-only, personal mode), jadi tidak bisa diuji dari luar. Endpoint `/clips/{id}` diuji dengan DB kosong. |
| **API2 Broken Authentication** | **Parsial–Kuat** | `401` untuk anonymous di semua endpoint terproteksi, JWT dari `/auth/bridge` diterima, rate limit `429`. Session Google nyata belum tervalidasi (UAT-01/02 diblokir browser otomatis). |
| **API3 Broken Object Property Level Authorization** | **Parsial** | Tidak ada alert *excessive data exposure* pada respons GET; `response_model` sudah ditambahkan ke dashboard/tools/ops (D-09). Mass assignment tidak diuji karena guard melarang POST/PATCH. |
| **API4 Unrestricted Resource Consumption** | **Parsial** | Rate limit 30/menit terverifikasi (`429`); pagination memakai `Query(ge/le)` pada endpoint daftar. ZAP tidak melakukan load/DoS testing. |
| **API5 Broken Function Level Authorization** | **Parsial** | Semua endpoint butuh JWT; `require_owner` dipakai untuk `/tools/model-status`. Tidak ada peran/user kedua untuk membuktikan eskalasi fungsi. |
| **API6 Unrestricted Access to Sensitive Business Flows** | **Tidak bisa dari luar** | Penyalahgunaan alur bisnis (brief→render→publish) butuh threat modelling; guard sengaja memblokir non-GET supaya tidak ada efek samping. |
| **API7 Server Side Request Forgery (SSRF)** | **Tidak diuji** | Plan hanya GET read-only. Endpoint dengan input URL (`/clips/generate-clips`, `/agent/shorts`) tidak dimasukkan ke spec aman; `/tools/dub` memakai `resolve_confined_path`. Perlu pengujian khusus dengan callback out-of-band. |
| **API8 Security Misconfiguration** | **Kuat** | Security headers lengkap (nosniff, DENY, referrer, permissions, COOP, COEP `credentialless`, CORP, HSTS, X-Permitted-Cross-Domain-Policies, CSP global + CSP CDN untuk docs), 0 alert; RabbitMQ non-`guest`, UI `15672` localhost; OpenAPI path lama = 0. |
| **API9 Improper Inventory Management** | **Parsial–Kuat** | `tests/test_docs_openapi_sync.py` menjaga snapshot OpenAPI tetap sinkron; 47 path terdokumentasi, 0 path lama. Global `security` didefinisikan (JWT Bearer + opsi anonim untuk endpoint publik) dan semua schema array punya `maxItems` (CKV_OPENAPI_4/5/21 → 5 passed, 0 failed). Lifecycle deprecasi/versioning tetap perlu review manual. |
| **API10 Unsafe Consumption of APIs** | **Tidak tercakup runtime** | Backend memanggil Exa/YouTube/Ollama/Pinecone; review source & validasi respons perlu dilakukan terpisah. Tidak ada bukti ZAP untuk kategori ini. |

Ringkasan: ZAP kuat di **API8**, memberi bukti sebagian untuk **API2/API3/API4/API5/API9**,
dan **tidak bisa** membuktikan **API1/API6/API7/API10** dengan cakupan saat ini.
Jangan melaporkan ini sebagai "lolos OWASP API Security Top 10 penuh". Tidak ada
Strix yang terlibat dalam pemetaan maupun scan ini.

## Penutup A03 & A09 (tool pendukung, bukan ZAP)

### A03 — Software Supply Chain
SCA dijalankan terpisah dari ZAP karena ZAP tidak mengaudit isi lockfile:

```powershell
uv export --frozen --no-dev --format requirements-txt -o temp/requirements-audit.txt
uvx pip-audit -r temp/requirements-audit.txt -f json > temp/pip-audit.json
cd frontend && bun audit --json > ../temp/bun-audit.json
uv run python scripts/audit_dependencies.py
```

`scripts/audit_dependencies.py` menggagalkan build bila ada severity **High/Critical**.
Temuan frontend (`vitest` 3.x, `tinypool` 1.1.1, `postcss-selector-parser` 6.0.10)
sudah diperbaiki: `vitest` → `^4.1.12` dan override `postcss-selector-parser`
→ `^6.1.5`; `bun audit` sekarang **0 temuan**, dan gate frontend tetap hijau
(typecheck, lint, check, vitest 3 test, e2e 49 test, build).

### A09 — Logging & Alerting
`scripts/audit_logs.py` memindai `logs/trace.jsonl` dan `logs/audit.jsonl` untuk
kunci sensitif dan pola secret/JWT. Dijalankan di CI setelah scan ZAP:

```powershell
uv run python scripts/audit_logs.py
```

Hasil lokal: **6.635 baris, 0 secret/JWT**. Ini melengkapi bukti source-level
(rotasi ukuran + redaksi di `backend/core/rotating_jsonl.py`, test
`tests/test_log_rotation.py`). Catatan jujur: **alerting aktif belum ada** — project
pribadi lokal tidak punya pipeline notifikasi; review ini hanya membuktikan log
aman, bukan bahwa alert dikirim.
