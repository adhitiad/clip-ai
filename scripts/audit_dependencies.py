"""Ringkas hasil SCA (A03) dari pip-audit dan bun audit; gagal pada High/Critical."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = (
    ROOT / "temp" / "pip-audit.json",
    ROOT / "temp" / "bun-audit.json",
)

BLOCKING = {"high", "critical"}


def _collect_severities(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "severity" and isinstance(item, str):
                out.append(item.strip().lower())
            _collect_severities(item, out)
        return
    if isinstance(value, list):
        for item in value:
            _collect_severities(item, out)


def main() -> int:
    severities: list[str] = []
    for report in REPORTS:
        if not report.is_file():
            print(f"SCA: laporan tidak ada, lewati: {report.name}")
            continue
        raw = report.read_text(encoding="utf-8").strip()
        if not raw:
            print(f"SCA: laporan kosong, lewati: {report.name}")
            continue
        try:
            data = json.loads(raw)
        except ValueError as exc:
            print(f"SCA GAGAL: {report.name} bukan JSON: {exc}")
            return 1
        before = len(severities)
        _collect_severities(data, severities)
        print(f"SCA {report.name}: {len(severities) - before} entri severity")

    bad = [item for item in severities if item in BLOCKING]
    if bad:
        print(f"SCA GAGAL: {len(bad)} temuan High/Critical ({sorted(set(bad))})")
        return 1
    print(f"SCA OK: {len(severities)} entri severity, 0 High/Critical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
