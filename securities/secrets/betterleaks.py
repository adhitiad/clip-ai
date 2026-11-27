"""Secret scanning: BetterLeaks terhadap seluruh history git."""

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

    report = report_path("betterleaks")
    baseline = CONFIG_DIR / "betterleaks-baseline.json"
    run_tool(
        "betterleaks",
        [
            "--baseline-path",
            str(baseline),
            "git",
            str(ROOT),
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ],
        allow_failure=args.allow_failure,
    )
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
