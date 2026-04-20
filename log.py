import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _configure_console_encoding():
    """
    Hindari UnicodeEncodeError di Windows console (cp1252) saat log mengandung emoji/unicode.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Tidak semua environment mendukung reconfigure (mis. redirected stream)
            pass

# Pastikan folder logs ada
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

_configure_console_encoding()

# Konfigurasi Dasar
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output ke Konsol
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),  # Output ke File (max 10MB)
    ]
)

# Logger utama untuk aplikasi
logger = logging.getLogger("clip_ai")
