"""Cetak jumlah worker Taskiq yang disarankan (inti fisik, genap untuk 2+ core)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.worker_count import recommended_workers  # noqa: E402

if __name__ == "__main__":
    print(recommended_workers())
