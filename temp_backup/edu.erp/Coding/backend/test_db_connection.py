"""
Test script to verify database connection
Run this from the backend directory: python test_db_connection.py
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Get database config
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3307")
DB_NAME = os.getenv("DB_NAME")

print("=" * 50)
print("DATABASE CONFIGURATION")
print("=" * 50)
print(f"Host: {DB_HOST}")
print(f"Port: {DB_PORT}")
print(f"Username: {DB_USERNAME}")
print(f"Database: {DB_NAME}")
print(f"Password: {'*' * len(DB_PASSWORD) if DB_PASSWORD else 'NOT SET'}")
print("=" * 50)

# Test connection
try:
    import pymysql
    connection = pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print("✅ DATABASE CONNECTION SUCCESSFUL!")
    
    # Get database info
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"📊 Database Version: {version[0]}")
    
    # List tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"📋 Number of Tables: {len(tables)}")
    print("Tables in database:")
    for table in tables[:10]:  # Show first 10 tables
        print(f"  - {table[0]}")
    if len(tables) > 10:
        print(f"  ... and {len(tables) - 10} more tables")
    
    cursor.close()
    connection.close()
    print("=" * 50)
    print("✅ ALL TESTS PASSED!")
    
except pymysql.Error as e:
    print("❌ DATABASE CONNECTION FAILED!")
    print(f"Error: {e}")
    print("\nPossible causes:")
    print("1. Wrong credentials in .env file")
    print("2. Database server not running")
    print("3. Wrong host/port")
    print("4. Database doesn't exist")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
