import datetime
import sys

# Fix encoding untuk Windows CMD
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

print(datetime.datetime.now(), "Testing bcrypt")
try:
    import bcrypt

    print("bcrypt imported, version:", getattr(bcrypt, "__version__", "unknown"))
    h = bcrypt.hashpw(b"test", bcrypt.gensalt())
    print("hash length:", len(h))
    print(datetime.datetime.now(), "Testing DB")
    import os
    from dotenv import load_dotenv
    from backend.utils.db import SessionLocal, init_db

    print("init DB")
    init_db()
    print("DB initialized")
except Exception as e:
    import traceback

    traceback.print_exc()
