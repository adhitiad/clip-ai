"""Central .env loading with a predictable precedence.

Process environment wins, then the component file (``backend/.env`` or
``workers/.env``), then the shared root ``.env``. Component files are loaded
first so their values win when the same key appears in both files.
"""

import os
from pathlib import Path

from dotenv import dotenv_values

ROOT_DIR = Path(__file__).resolve().parents[2]


def load_env(component: str | None = None) -> None:
    paths: list[Path] = []
    if component:
        paths.append(ROOT_DIR / component / ".env")
    paths.append(ROOT_DIR / ".env")

    for path in paths:
        if not path.is_file():
            continue
        for key, value in dotenv_values(path).items():
            if value is not None:
                os.environ.setdefault(key, value)
