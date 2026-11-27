# Security toolkit — referensi

Semua path relatif terhadap root repo. Tidak ada MCP; semua scanner dijalankan
dengan `uv run python securities/...` atau langsung dari `securities/bin`.

## Tool

| Tool | Kategori | Wrapper | Laporan |
| --- | --- | --- | --- |
| Semgrep CE | SAST Python/TS | `securities/sast/semgrep.py` | `reports/semgrep.json` |
| Trivy | FS/image, SCA, secret, misconfig | `securities/sca/trivy.py` | `reports/trivy-fs.json`, `reports/trivy-images.json` |
| OSV-Scanner | SCA lockfile (`uv.lock`, `bun.lock`) | `securities/sca/osv_scanner.py` | `reports/osv-scanner.json` |
| Gitleaks | Secret scanning (history) | `securities/secrets/gitleaks.py` | `reports/gitleaks.json` |
| BetterLeaks | Secret scanning (history) | `securities/secrets/betterleaks.py` | `reports/betterleaks.json` |
| Hadolint | Dockerfile lint | `securities/iac/hadolint.py` | `reports/hadolint.json` |
| Checkov | Dockerfile/Compose/CI config | `securities/iac/checkov.py` | `reports/checkov.json` |
| Nuclei | Template-based DAST | `securities/dast/nuclei.py` | `reports/nuclei.json` |
| OWASP ZAP | DAST + auth scan | `scripts/zap_auth_scan.py`, `zap-scan.yaml` | `zap-report-auth.json`, `zap-report.json` |

## Opsi umum

- `--allow-failure`: lanjutkan scanner berikutnya walau ada temuan.
- `run_all.py --include-nuclei`: sertakan Nuclei; butuh API di `127.0.0.1:8000`.
- `trivy.py --scan-images`: scan image Docker yang sudah dibangun.
- `nuclei.py --url <url> --templates <comma-separated>`: ganti target/template.

## Config

- `securities/configs/semgrep.yml` — aturan eval/exec dan `shell=True`.
- `securities/configs/gitleaks.toml` — extend default Gitleaks.
- `securities/configs/hadolint.yaml` — threshold warning,abaikan DL3008/DL3009.
- `securities/configs/checkov.yaml` — output json, skip aturan Kubernetes.
- `securities/configs/osv-scanner.toml` — placeholder override.

## Cara membaca laporan

- Semgrep: `results` dan `errors`; 0/0 berhasil.
- Trivy: `Results[].Vulnerabilities` dan `Results[].Secrets` / `Misconfigurations`.
- OSV-Scanner: `results[].packages[].vulnerabilities`.
- Gitleaks/BetterLeaks: array kosong berarti tidak ada secret; ada entri perlu triage.
- Hadolint: array entri dengan `code`, `filename`, `line`, `message`.
- Checkov: `results.failed_checks` dan `results.passed_checks`.
- Nuclei: array event dengan `severity`, `template-id`, `matched-at`.

## Batas cakupan (jujur)

- **A01/BOLA & API1**: tidak bisa dibuktikan tanpa akun/tenant kedua. Project ini
  single-user.
- **SSRF**: endpoint ber-URL tidak ikut spec aman ZAP; butuh pengujian callback
  khusus.
- **A03 Supply Chain**: ZAP tidak mengaudit lockfile; gunakan Trivy/OSV/pip-audit/
  bun audit (sudah ada di CI).
- **A09 Logging**: tidak bisa diuji dari luar; bukti berupa `scripts/audit_logs.py`
  dan `tests/test_log_rotation.py`.
- **Auth Google nyata**: alur OAuth belum lolos dari browser otomatis; perlu browser
  normal pemilik repo.

## Keamanan operasional

- Jangan commit `securities/bin`, `uv-tools`, `reports`, `.download` (sudah gitignored).
- Jangan menempelkan JWT/API key ke ringkasan atau PR comment.
- Simpan temuan sebagai ringkasan; jangan menyalin isi secret mentah.
- Untuk perbaikan, ikuti alur: temuan → PoC/konfirmasi → patch → scan ulang → gate.
