"""SCA lockfile: OSV-Scanner untuk uv.lock dan frontend/bun.lock."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEC_ROOT))

from lib.common import ROOT, report_path, run_tool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    report = report_path("osv-scanner")
    run_tool(
        "osv-scanner",
        [
            "scan",
            "--format",
            "json",
            "--output-file",
            str(report),
            "-L",
            str(ROOT / "uv.lock"),
            "-L",
            str(ROOT / "frontend" / "bun.lock"),
        ],
        allow_failure=args.allow_failure,
    )
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
