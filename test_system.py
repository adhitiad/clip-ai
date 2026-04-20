import datetime
print(datetime.datetime.now(), "Testing bcrypt")
try:
    import bcrypt
    print("bcrypt imported, version:", getattr(bcrypt, "__version__", "unknown"))
    h = bcrypt.hashpw(b"test", bcrypt.gensalt())
    print("hash length:", len(h))
    print(datetime.datetime.now(), "Testing DB")
    import os
    from dotenv import load_dotenv
    from utils.db import SessionLocal, init_db
    print("init DB")
    init_db()
    print("DB initialized")
except Exception as e:
    import traceback
    traceback.print_exc()
