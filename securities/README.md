# Security toolkit — Clip AI

Kumpulan scanner gratis/open-source yang dipasang **lokal di folder ini**, bukan global.
Semua wrapper memakai Python dan dijalankan dari root repo dengan `uv`.

## Struktur

```
securities/
  bin/            # binary + uv tool shim (gitignored)
  uv-tools/       # uv tool install directory (gitignored)
  reports/        # hasil scan JSON (gitignored)
  configs/        # konfigurasi per tool
  lib/common.py   # resolver tool + path laporan
  sast/semgrep.py
  sca/trivy.py, sca/osv_scanner.py
  secrets/gitleaks.py, secrets/betterleaks.py
  iac/hadolint.py, iac/checkov.py
  dast/nuclei.py
  bootstrap.py    # download/pasang semua tool
  run_all.py      # jalankan semua scanner
```

## Pasang

```powershell
uv run python securities/bootstrap.py
```

Bootstrap mengunduh binary Windows/Linux/macOS dari GitHub Releases ke `securities/bin`,
dan memasang `semgrep` + `checkov` via `uv tool` dengan `UV_TOOL_DIR` di folder ini.

## Jalankan

Semua scanner (kecuali Nuclei):

```powershell
uv run python securities/run_all.py
```

Termasuk Nuclei (butuh API lokal jalan di `127.0.0.1:8000`):

```powershell
uv run python securities/run_all.py --include-nuclei
```

Per tool:

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

Tambahkan `--allow-failure` bila ingin tetap lanjut meski scanner menemukan masalah.
Semua laporan ditulis ke `securities/reports/*.json`.

## Baseline BetterLeaks

`securities/configs/betterleaks-baseline.json` berisi 13 temuan historis yang
sudah ditriage: URL koneksi contoh (`user:password`, `postgres:password`) dan
password seed lama (`Owner@12345`, `Staff@12345`, `User@12345`) di `README.md`,
`.env.example`, dan `scripts/seed_db.py`. Wrapper `secrets/betterleaks.py`
memakai `--baseline-path`, jadi rule tetap aktif untuk temuan baru. Jangan
mematikan rule global.

## Scope scan

Trivy `--skip-dirs` dan Checkov `--skip-path` memakai daftar di
`securities/lib/common.py` (`SKIP_DIRS` / `SKIP_PATTERNS`) agar tidak memindai
dependency pihak ketiga, tool scanner, result scan, cache, dan data lokal:
`.venv`, `node_modules`, `securities/bin`, `securities/uv-tools`,
`securities/reports`, `temp`, `output`, `logs`, `download`, `backups`,
`client_secret*`, dll. Dengan scope ini Trivy fokus pada 6 target source
(`requirements.txt`, `bun.lock`, `uv.lock`, 3 Dockerfile) dan Checkov OpenAPI
menjadi 5 passed / 0 failed. Temuan yang tersisa adalah konfigurasi nyata
(mis. `CKV_DOCKER_2/3` pada Dockerfile dan basic auth di `docker-compose.yml`),
bukan false positive dari tool.

## Catatan
- Tidak ada Strix di toolkit ini.
- Nuclei memakai template komunitas; jalankan
  `securities/bin/nuclei.exe -update-templates` sekali bila template belum ada.
- Tool di sini melengkapi ZAP, bukan menggantikan ZAP untuk DAST.
