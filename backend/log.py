import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from backend.core.request_id import get_request_id


def _configure_console_encoding():
    """Hindari UnicodeEncodeError di console Windows (cp1252) saat log emoji/unicode."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                # Tidak semua stream mendukung reconfigure (mis. redirected).
                pass


LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
_configure_console_encoding()

LOG_FILE = os.path.join(LOG_DIR, "app.log")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


logger = logging.getLogger("clip_ai")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    request_filter = RequestIdFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(request_filter)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(request_filter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
