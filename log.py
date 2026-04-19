import logging
import os
from logging.handlers import RotatingFileHandler

# Pastikan folder logs ada
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Konfigurasi Dasar
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Output ke Konsol
        RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5) # Output ke File (max 10MB)
    ]
)

# Logger utama untuk aplikasi
logger = logging.getLogger("clip_ai")
