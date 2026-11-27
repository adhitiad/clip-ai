"""DAST template-based: Nuclei (butuh target yang sudah berjalan)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEC_ROOT))

from lib.common import report_path, run_tool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--templates", default="http/misconfiguration,http/exposures")
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    report = report_path("nuclei")
    run_tool(
        "nuclei",
        ["-u", args.url, "-t", args.templates, "-json-export", str(report), "-silent"],
        allow_failure=args.allow_failure,
    )
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
