import os
import aiomysql
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
# from ..core.constants import DB_USERNAME, DB_PASSWORD, DB_HOST, DB_NAME,DB_PORT

dotenv_path = os.path.join(".env")
load_dotenv(dotenv_path=dotenv_path)


DB_USERNAME = os.getenv("DB_USERNAME") or ""
DB_PASSWORD = os.getenv("DB_PASSWORD") or ""
DB_HOST = os.getenv("DB_HOST") or ""
DB_PORT = int(os.getenv("DB_PORT", 3307))
DB_NAME = os.getenv("DB_NAME") or ""

# URL encode the password to handle special characters like @
ENCODED_PASSWORD = quote(DB_PASSWORD, safe='')

# Use PyMySQL driver for MariaDB compatibility
DATABASE_URL =  "mysql+pymysql://root:root@localhost:3307/ionerp_lms_19_02_2026"
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        
async def get_db_pool():
    port = int(DB_PORT)  # Convert the port to an integer
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
