"""Dockerfile lint: Hadolint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEC_ROOT))

from lib.common import CONFIG_DIR, ROOT, report_path, run_tool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    dockerfiles = [
        ROOT / "Dockerfile",
        ROOT / "Dockerfile.render-worker",
        ROOT / "frontend" / "Dockerfile",
    ]
    result = run_tool(
        "hadolint",
        [
            "--config",
            str(CONFIG_DIR / "hadolint.yaml"),
            "--format",
            "json",
            *[str(p) for p in dockerfiles],
        ],
        allow_failure=args.allow_failure,
        capture=True,
    )
    report = report_path("hadolint")
    report.write_text(result.stdout, encoding="utf-8")
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
