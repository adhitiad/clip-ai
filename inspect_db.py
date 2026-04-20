import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/clip_ai")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("--- Table Columns ---")
        inspector = inspect(engine)
        columns = inspector.get_columns("users")
        for col in columns:
            print(f"Column: {col['name']}, Type: {col['type']}")
        
        print("\n--- Custom Enum Types ---")
        result = conn.exec_driver_sql("SELECT t.typname, array_agg(e.enumlabel) FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid GROUP BY t.typname").fetchall()
        for row in result:
            print(f"Type: {row[0]}, Values: {row[1]}")
except Exception as e:
    print("Error:", e)
