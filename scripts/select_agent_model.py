"""Pilih AGENT_MODEL secara interaktif lalu simpan ke .env.

Jalankan dari root repo:
    uv run python scripts/select_agent_model.py

Alur:
  1. Cari model tersedia dari API provider (bila key ada) + katalog.
  2. Pilih nomor, ATAU ketik manual 'provider/model' bila tidak ada/ingin lain.
  3. Simpan AGENT_PROVIDER & AGENT_MODEL ke .env (baris lain tidak berubah).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.env import load_env  # noqa: E402

load_env("backend")

from backend.services.model_discovery import (  # noqa: E402
    save_model_choice,
    select_provider_model,
)


def main() -> int:
    provider, model = select_provider_model()
    path = save_model_choice(provider, model)
    print(f"\nTersimpan: {path}")
    print(f"  AGENT_PROVIDER={provider}")
    print(f"  AGENT_MODEL={model}")
    print("\nJalankan: uv run python scripts/gate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
