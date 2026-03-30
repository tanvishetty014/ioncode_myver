
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

# URL encode password
ENCODED_PASSWORD = quote(DB_PASSWORD, safe="")

# Database URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USERNAME}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# Keep DB_USERNAME name for backward compatibility elsewhere in the codebase
DB_USERNAME = DB_USER

# URL encode the password to handle special characters (safe fallback if None)
ENCODED_PASSWORD = quote(DB_PASSWORD or "", safe='')

# Construct DATABASE_URL using the environment variables
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Temporary debug print (remove after testing)
try:
    print(f"DEBUG: DB_USER={DB_USER}, DB_NAME={DB_NAME}")
except Exception:
    pass


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