import os

# Konfigurasi import-time:
# - Saat dijalankan lewat scripts/gate.py, GATE_ENV menimpa DATABASE_URL ke PostgreSQL.
# - Saat pytest dijalankan sendiri, pakai SQLite agar tetap hermetik.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./.test.db")
os.environ.setdefault("DUB_ALLOWED_ROOT", "temp")
