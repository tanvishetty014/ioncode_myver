"""
Database Setup Script
This script will:
1. Create the database if it doesn't exist
2. Test the connection

Run: python setup_database.py
"""
import pymysql
import os
from dotenv import load_dotenv

# Load .env file
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Get config (try .env.new if .env doesn't have port)
DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3307))
DB_NAME = os.getenv("DB_NAME", "ionerp_lms_19_02_2026")

print("=" * 50)
print("DATABASE SETUP")
print("=" * 50)
print(f"Host: {DB_HOST}")
print(f"Port: {DB_PORT}")
print(f"Username: {DB_USERNAME}")
print(f"Database: {DB_NAME}")
print("=" * 50)

# First connect WITHOUT database to create it
print("\n1. Connecting to MySQL server...")
try:
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USERNAME,
        password=DB_PASSWORD
    )
    print("✅ Connected to MySQL server!")
    
    cursor = connection.cursor()
    
    # Check if database exists
    cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Database '{DB_NAME}' already exists!")
    else:
        print(f"\n2. Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"✅ Database '{DB_NAME}' created successfully!")
    
    cursor.close()
    connection.close()
    
    # Now test connection WITH database
    print("\n3. Testing connection to database...")
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print("✅ Database connection successful!")
    
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"📋 Tables in database: {len(tables)}")
    
    cursor.close()
    connection.close()
    
    print("\n" + "=" * 50)
    print("✅ DATABASE SETUP COMPLETE!")
    print("=" * 50)
    
except pymysql.Error as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure MySQL/MariaDB is running")
    print("2. Check username and password")
    print(f"3. Verify port {DB_PORT} is correct")
