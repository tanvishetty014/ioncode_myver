import os
import aiomysql
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
from pathlib import Path

# ─── 1. FIND AND LOAD THE .ENV FILE ───────────────────────────────────────────
# This logic checks the current folder and parent folders to find your .env
current_file_path = Path(__file__).resolve()
possible_env_paths = [
    current_file_path.parent / ".env",          # Same folder
    current_file_path.parent.parent / ".env",   # One level up
    current_file_path.parent.parent.parent / ".env" # Two levels up
]

env_found = False
for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break

# ─── 2. READ THE ENVIRONMENT VARIABLES ───────────────────────────────────────
DB_USERNAME = os.getenv("DB_USERNAME", "NOT_FOUND").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_HOST     = os.getenv("DB_HOST", "localhost").strip()
DB_PORT     = os.getenv("DB_PORT", "3306").strip()
DB_NAME     = os.getenv("DB_NAME", "").strip()

# ─── 3. DEBUG PRINT (Check your terminal for these lines!) ────────────────────
print("\n" + "="*30)
print("DATABASE CONNECTION DEBUG")
print(f"Status: {'.env file found' if env_found else '.env NOT FOUND'}")
print(f"User:   {DB_USERNAME}")
print(f"DB:     {DB_NAME}")
print("="*30 + "\n")

# ─── 4. CONSTRUCT DATABASE URL ───────────────────────────────────────────────
# We use quote() to handle any special characters in the password
ENCODED_PASSWORD = quote(DB_PASSWORD, safe="")
DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ─── 5. SQLALCHEMY SETUP (Synchronous) ───────────────────────────────────────
# pool_pre_ping=True prevents "Connection Lost" errors
# pool_recycle helps avoid timing out with MySQL
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True, 
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Sync DB Dependency (used in your FastAPI routes)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── 6. ASYNC POOL SETUP (For aiomysql logic) ────────────────────────────────
async def get_db_pool():
    # Ensure port is an integer
    port_int = int(DB_PORT)
    return await aiomysql.create_pool(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        db=DB_NAME,
        port=port_int,
        autocommit=True,
        minsize=1,
        maxsize=10
    )
