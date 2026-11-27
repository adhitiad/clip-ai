"""SAST: Semgrep CE terhadap backend/frontend/workers/scripts."""

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
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    paths = args.paths or [
        str(ROOT / "backend"),
        str(ROOT / "frontend" / "src"),
        str(ROOT / "workers"),
        str(ROOT / "scripts"),
    ]
    report = report_path("semgrep")
    run_tool(
        "semgrep",
        [
            "scan",
            "--config",
            str(CONFIG_DIR / "semgrep.yml"),
            "--json",
            "--output",
            str(report),
            *paths,
        ],
        allow_failure=args.allow_failure,
    )
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
