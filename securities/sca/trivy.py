"""SCA/konfigurasi: Trivy filesystem atau image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEC_ROOT))

from lib.common import ROOT, SKIP_DIRS, report_path, run_tool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="")
    parser.add_argument("--scan-images", action="store_true")
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    if args.scan_images:
        report = report_path("trivy-images")
        run_tool(
            "trivy",
            [
                "image",
                "--format",
                "json",
                "--output",
                str(report),
                "clip-ai-api:latest",
                "clip-ai-worker:latest",
                "clip-ai-render-worker:latest",
                "clip-ai-frontend:latest",
            ],
            allow_failure=args.allow_failure,
        )
    else:
        report = report_path("trivy-fs")
        target = args.target or str(ROOT)
        cmd = [
            "fs",
            "--scanners",
            "vuln,secret,misconfig",
            "--timeout",
            "10m",
        ]
        for directory in SKIP_DIRS:
            cmd.extend(["--skip-dirs", directory])
        cmd.extend(
            [
                "--format",
                "json",
                "--output",
                str(report),
                target,
            ]
        )
        run_tool("trivy", cmd, allow_failure=args.allow_failure)
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
