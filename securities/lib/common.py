"""Utilitas bersama untuk toolkit security (dijalankan dari root repo dengan uv)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SEC_ROOT = Path(__file__).resolve().parents[1]
ROOT = SEC_ROOT.parent
BIN_DIR = SEC_ROOT / "bin"
REPORT_DIR = SEC_ROOT / "reports"
CONFIG_DIR = SEC_ROOT / "configs"
UV_TOOLS_DIR = SEC_ROOT / "uv-tools"
IS_WINDOWS = sys.platform == "win32"

# Direktori yang bukan source aplikasi. Tidak perlu dipindai SCA/IaC:
# dependency pihak ketiga, tool scanner, hasil render, cache, dan data lokal.
# Regex untuk Checkov --skip-path (pola nama, bukan path penuh).
SKIP_PATTERNS = (
    ".venv",
    "uv-tools",
    "securities/reports",
    "reports",
    "betterleaks-baseline",
    "client_secret",
    "node_modules",
    "temp",
    "output",
    "logs",
    "download",
    "backups",
)

SKIP_DIRS = (
    ".venv",
    "venv",
    "node_modules",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    "securities/bin",
    "securities/uv-tools",
    "securities/reports",
    "temp",
    "output",
    "logs",
    "download",
    "backups",
    "frontend/dist",
    "frontend/node_modules",
)


def ensure_dirs() -> None:
    for path in (BIN_DIR, REPORT_DIR, CONFIG_DIR, UV_TOOLS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def report_path(name: str) -> Path:
    ensure_dirs()
    return REPORT_DIR / f"{name}.json"


def resolve_tool(name: str) -> list[str]:
    """Kembalikan perintah lengkap (bisa lebih dari satu argumen)."""
    ensure_dirs()

    if name == "checkov":
        scripts = UV_TOOLS_DIR / "checkov" / ("Scripts" if IS_WINDOWS else "bin")
        python = scripts / ("python.exe" if IS_WINDOWS else "python")
        entry = scripts / ("checkov" if IS_WINDOWS else "checkov")
        if python.is_file() and entry.is_file():
            return [str(python), str(entry)]
        for candidate in (
            BIN_DIR / "checkov.bat",
            BIN_DIR / "checkov.cmd",
            BIN_DIR / "checkov",
        ):
            if candidate.is_file():
                return [str(candidate)]

    candidates = [BIN_DIR / f"{name}.exe", BIN_DIR / name]
    for candidate in candidates:
        if candidate.is_file():
            return [str(candidate)]

    raise SystemExit(
        f"Tool '{name}' belum terpasang di {BIN_DIR}. "
        f"Jalankan: uv run python securities/bootstrap.py"
    )


def run_tool(
    name: str,
    args: list[str],
    *,
    allow_failure: bool = False,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [*resolve_tool(name), *args]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(result.returncode)
    return result


def uv_tool_env() -> dict[str, str]:
    return {
        **os.environ,
        "UV_TOOL_DIR": str(UV_TOOLS_DIR),
        "UV_TOOL_BIN_DIR": str(BIN_DIR),
    }
