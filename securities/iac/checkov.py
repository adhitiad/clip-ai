"""IaC / Docker / CI config: Checkov."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SEC_ROOT))

from lib.common import (  # noqa: E402
    CONFIG_DIR,
    REPORT_DIR,
    ROOT,
    SKIP_PATTERNS,
    report_path,
    run_tool,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-failure", action="store_true")
    args = parser.parse_args()

    report = report_path("checkov")
    legacy = REPORT_DIR / "checkov.json"
    if legacy.is_dir():
        shutil.rmtree(legacy)

    cmd = [
        "--directory",
        str(ROOT),
        "--config-file",
        str(CONFIG_DIR / "checkov.yaml"),
    ]
    for pattern in SKIP_PATTERNS:
        cmd.extend(["--skip-path", pattern])
    cmd.extend(
        [
            "--output",
            "json",
            "--output-file-path",
            str(REPORT_DIR),
            "--quiet",
        ]
    )
    run_tool("checkov", cmd, allow_failure=args.allow_failure)
    generated = REPORT_DIR / "results_json.json"
    if generated.is_file():
        shutil.move(str(generated), report)
    print(f"Laporan: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
