---
name: security
description: Run and triage the repository's MCP-free security toolkit (Trivy, Semgrep, Gitleaks, BetterLeaks, OSV-Scanner, Hadolint, Checkov, Nuclei, OWASP ZAP). Use when asked to scan or audit this repo, check secrets, dependencies, Dockerfiles, APIs, triage findings, or write a security report. No MCP server is required.
---

# Security (Clip AI)

Toolkit init berada di `securities/` di root repo. Semua scanner dijalankan lokal
memakai `uv`, tanpa MCP, tanpa Strix, dan tanpa mengirim kode ke layanan eksternal
kecuali lookup vulnerability database bawaan tool.

## Aturan utama

- Jalankan semua perintah Python dari **root repo** dengan `uv run python ...`.
- Jangan pernah mencetak atau menyalin secret/JWT ke chat atau laporan.
- Laporan scan masuk ke `securities/reports/*.json` dan **gitignored**.
- Jangan otomatis memperbaiki temuan. Ringkas, minta keputusan, lalu perbaiki
  satu per satu dan jalankan ulang scanner yang relevan.
- Hanya scan target milik user / repo ini.
- Setelah mengubah kode, jalankan `uv run python scripts/gate.py` dan gate frontend
  dari `frontend/`.

## Langkah 1 — Pastikan tool terpasang

```powershell
uv run python securities/bootstrap.py
```

Binary ada di `securities/bin`, tool Python (Semgrep, Checkov) di `securities/uv-tools`.
Bootstrap bisa dijalankan ulang; tool yang sudah ada akan dilewati.

## Langkah 2 — Jalankan scan

Semua scanner kecuali Nuclei:

```powershell
uv run python securities/run_all.py
```

Semua scanner termasuk Nuclei (butuh API jalan di `127.0.0.1:8000`):

```powershell
uv run python securities/run_all.py --include-nuclei
```

Tambahkan `--allow-failure` bila ingin tetap menyelesaikan semua scanner walaupun
ada temuan. Gunakan untuk triage, bukan untuk menyatakan "aman".

Per kategori:

```powershell
uv run python securities/sast/semgrep.py
uv run python securities/sca/trivy.py
uv run python securities/sca/trivy.py --scan-images
uv run python securities/sca/osv_scanner.py
uv run python securities/secrets/gitleaks.py
uv run python securities/secrets/betterleaks.py
uv run python securities/iac/hadolint.py
uv run python securities/iac/checkov.py
uv run python securities/dast/nuclei.py --url http://127.0.0.1:8000
```

ZAP (DAST terautentikasi, SQLite terisolasi + guard read-only):

```powershell
uv run python scripts/zap_auth_scan.py
```

Scan anonymous memakai `zap-scan.yaml` dengan ZAP lokal. CI menjalankan keduanya
lewat `.github/workflows/security-zap.yml`.

## Langkah 3 — Ringkas dan triage

Baca `securities/reports/*.json` dan `zap-report-auth.json`. Kelompokkan temuan
menjadi **Critical / High / Medium / Low / Info**. Untuk tiap temuan:
1. sebutkan tool, path/endpoint, dan severity;
2. jelaskan apakah benar-benar reachable atau false positive;
3. usulkan perbaikan minimum;
4. jangan langsung mengubah kode tanpa konfirmasi.

Nyatakan cakupan dengan jujur: ZAP menutup A02/A05 dengan baik, tetapi tidak bisa
membuktikan BOLA tanpa akun kedua, SSRF tanpa callback, A03 tanpa SCA, dan A09 tanpa
review log. Lihat `references/toolkit.md` untuk pemetaan detail dan batas cakupan.

## Langkah 4 — Verifikasi setelah perbaikan

Jalankan ulang scanner yang relevan, lalu:

```powershell
uv run python scripts/gate.py
cd frontend; bun --bun run typecheck; bun --bun run lint; bun --bun run check; bun --bun run test:e2e; bun --bun run build
```

Laporkan perintah yang dijalankan dan hasilnya. Jangan klaim gate hijau tanpa output.
