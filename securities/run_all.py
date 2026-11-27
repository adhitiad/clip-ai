"""Jalankan semua scanner security satu per satu."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parent

JOBS = [
    ("semgrep", "sast/semgrep.py"),
    ("trivy", "sca/trivy.py"),
    ("osv-scanner", "sca/osv_scanner.py"),
    ("gitleaks", "secrets/gitleaks.py"),
    ("betterleaks", "secrets/betterleaks.py"),
    ("hadolint", "iac/hadolint.py"),
    ("checkov", "iac/checkov.py"),
]
NUCLEI = ("nuclei", "dast/nuclei.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-nuclei", action="store_true")
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    jobs = list(JOBS)
    if args.include_nuclei:
        jobs.append(NUCLEI)

    failed: list[str] = []
    for name, relative in jobs:
        print(f"\n=== {name} ===", flush=True)
        command = [sys.executable, str(SEC_ROOT / relative)]
        if args.allow_failure:
            command.append("--allow-failure")
        result = subprocess.run(command, cwd=SEC_ROOT.parent, check=False)
        if result.returncode != 0:
            failed.append(name)

    print("\n=== Ringkasan ===")
    if failed:
        print("Scanner gagal: " + ", ".join(failed))
        return 1 if not args.allow_failure else 0
    print(f"Semua scanner selesai. Laporan di: {SEC_ROOT / 'reports'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
