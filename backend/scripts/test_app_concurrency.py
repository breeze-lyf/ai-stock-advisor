import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def test_api():
    client = TestClient(app)
    
    print("\n[1/3] Testing Health Check...")
    try:
        response = client.get("/health", timeout=10)
        print(f"Health Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Health Failed: {e}")

    print("\n[2/3] Testing GET /api/macro/cls_news (Unauthenticated)...")
    try:
        # This should return 401/403 or hang if it's a dependency issue
        response = client.get("/api/macro/cls_news", timeout=10)
        print(f"News Status: {response.status_code}")
    except Exception as e:
        print(f"News Failed: {e}")

if __name__ == "__main__":
    test_api()
