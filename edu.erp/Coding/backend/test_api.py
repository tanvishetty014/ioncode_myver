"""
Test script to verify API is working and responding
Run this from the backend directory: python test_api.py
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

print("=" * 50)
print("TESTING API CONNECTION")
print("=" * 50)

# Test 1: Root endpoint
print("\n1. Testing root endpoint...")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to API. Is the backend running?")
    print("   Run: uvicorn app.main:app --reload")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: API v1 endpoint
print("\n2. Testing /api/v1 endpoint...")
try:
    response = requests.get(f"{BASE_URL}/api/v1", timeout=5)
    print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Error (may be expected if no route exists): {e}")

# Test 3: CORS check
print("\n3. Checking CORS headers...")
try:
    response = requests.options(f"{BASE_URL}/", timeout=5)
    cors_headers = response.headers.get('access-control-allow-origin', 'Not set')
    print(f"   CORS Allow Origin: {cors_headers}")
except Exception as e:
    print(f"   ⚠️  Error checking CORS: {e}")

print("\n" + "=" * 50)
print("✅ API CONNECTION TEST COMPLETE!")
print("=" * 50)
