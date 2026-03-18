import os
import aiomysql
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

# Clean + safe env handling (best version)
DB_USERNAME = (os.getenv("DB_USERNAME") or "").strip()
DB_PASSWORD = (os.getenv("DB_PASSWORD") or "").strip()
DB_HOST = (os.getenv("DB_HOST") or "localhost").strip()
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = (os.getenv("DB_NAME") or "").strip()

# URL encode password
ENCODED_PASSWORD = quote(DB_PASSWORD, safe="")

# Database URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USERNAME}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_db_pool():
    port = int(DB_PORT)
    return await aiomysql.create_pool(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        db=DB_NAME,
        port=port,
        autocommit=True,
        minsize=1,
        maxsize=10
    )