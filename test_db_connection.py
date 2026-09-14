import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is missing. Add it to your .env file.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("DB connection OK")
        print(result.scalar())
except Exception as exc:
    print(f"DB connection failed: {exc}")
    raise
