"""Run the full Python gate (menggunakan PostgreSQL, bukan SQLite).

Usage (dari root repo):
    uv sync
    uv run python scripts/gate.py

Default database: postgresql://postgres:password@localhost:5432/clip_ai
Override untuk CI/env lain lewat GATE_DATABASE_URL.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["backend", "workers", "scripts", "tests"]
GATE_ENV = {
    "SECRET_KEY": "gate-only-secret-key-0123456789abcdef",
    "GROQ_API_KEY": "gate-only-groq-key",
    "DATABASE_URL": os.environ.get(
        "GATE_DATABASE_URL", "postgresql://postgres:password@localhost:5432/clip_ai"
    ),
    "RABBITMQ_URL": os.environ.get(
        "GATE_RABBITMQ_URL", "amqp://guest:guest@localhost:5672//"
    ),
    "DUB_ALLOWED_ROOT": "temp",
}


def run(label: str, command: list[str]) -> bool:
    print(f"\n== {label} ==", flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, **GATE_ENV},
        text=True,
    )
    if result.returncode != 0:
        print(f"FAILED: {label}", file=sys.stderr)
        return False
    return True


def main() -> int:
    python = sys.executable
    steps = [
        ("ruff lint", [python, "-m", "ruff", "check", *TARGETS]),
        ("ruff format", [python, "-m", "ruff", "format", "--check", *TARGETS]),
        ("compileall", [python, "-m", "compileall", "-q", *TARGETS]),
        (
            "docs/openapi sync",
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/test_docs_openapi_sync.py",
            ],
        ),
        (
            "postgres connection",
            [
                python,
                "-c",
                "import os, sqlalchemy; "
                "e=sqlalchemy.create_engine(os.environ['DATABASE_URL']); "
                "c=e.connect(); print('postgres OK:', c.scalar(sqlalchemy.text('SELECT 1'))); c.close()",
            ],
        ),
        ("pytest", [python, "-m", "pytest", "-q"]),
        (
            "app import",
            [python, "-c", "import backend.main; print('backend.main OK')"],
        ),
        (
            "worker import",
            [
                python,
                "-c",
                "from workers.worker import broker; "
                "print('worker OK:', type(broker).__name__)",
            ],
        ),
    ]

    failed = [label for label, command in steps if not run(label, command)]
    if failed:
        print(f"\nGate failed: {', '.join(failed)}", file=sys.stderr)
        print(
            "Pastikan PostgreSQL jalan dan DATABASE_URL benar. "
            "Gunakan GATE_DATABASE_URL untuk override.",
            file=sys.stderr,
        )
        return 1
    print("\nGate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
