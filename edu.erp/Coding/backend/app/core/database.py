
import os
try:
    import aiomysql
except ImportError:
    aiomysql = None
try:
    from dotenv import load_dotenv
except Exception:
    # If python-dotenv is not installed in this environment, provide a no-op
    def load_dotenv(*a, **k):
        return None
try:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except Exception:
    # Provide safe placeholders when SQLAlchemy isn't installed (for quick env checks)
    def create_engine(*a, **k):
        return None

    def declarative_base():
        class _DummyBase:
            pass

        return _DummyBase

    def sessionmaker(*a, **k):
        def _sm(**kw):
            return None

        return _sm
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

<<<<<<< HEAD
# Clean + safe env handling (best version)
DB_USERNAME = (os.getenv("DB_USERNAME") or "").strip()
DB_PASSWORD = (os.getenv("DB_PASSWORD") or "").strip()
DB_HOST = (os.getenv("DB_HOST") or "localhost").strip()

# Ensure .env is loaded: prefer .env next to the backend root (two levels up),
# fall back to current working directory.
dotenv_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
)
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.abspath(os.path.join(os.getcwd(), ".env"))
load_dotenv(dotenv_path=dotenv_path)

# If python-dotenv wasn't available (load_dotenv was a no-op) try a simple
# manual parse of the .env file to populate os.environ for required keys.
if not os.getenv("DB_USER") and os.path.exists(dotenv_path):
    try:
        with open(dotenv_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

# Prefer explicit DB_USER env var but fall back to legacy DB_USERNAME if present
DB_USER = os.getenv("DB_USER") or os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = (os.getenv("DB_NAME") or "").strip()
=======
env_found = False
for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
>>>>>>> 03403f79f48c202752b10687ff8d046867d9239d

# ─── 2. READ THE ENVIRONMENT VARIABLES ───────────────────────────────────────
DB_USERNAME = os.getenv("DB_USERNAME", "NOT_FOUND").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_HOST     = os.getenv("DB_HOST", "localhost").strip()
DB_PORT     = os.getenv("DB_PORT", "3306").strip()
DB_NAME     = os.getenv("DB_NAME", "").strip()

# ─── 3. DEBUG PRINT (Check your terminal for these lines!) ────────────────────
print("\n" + "="*30)
print("🔍 DATABASE CONNECTION DEBUG")
print(f"Status: {'.env file found' if env_found else '❌ .env NOT FOUND'}")
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
# Keep DB_USERNAME name for backward compatibility elsewhere in the codebase
DB_USERNAME = DB_USER

# URL encode the password to handle special characters (safe fallback if None)
ENCODED_PASSWORD = quote(DB_PASSWORD or "", safe='')

# Construct DATABASE_URL using the environment variables
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

<<<<<<< HEAD
# Temporary debug print (remove after testing)
try:
    print(f"DEBUG: DB_USER={DB_USER}, DB_NAME={DB_NAME}")
except Exception:
    pass


=======
# Sync DB Dependency (used in your FastAPI routes)
>>>>>>> 03403f79f48c202752b10687ff8d046867d9239d
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