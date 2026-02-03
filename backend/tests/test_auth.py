from fastapi.testclient import TestClient
from app.main import app
import sys
import os

sys.path.append(os.getcwd())

client = TestClient(app)

def test_auth_flow():
    # 1. Register
    email = "test@example.com"
    password = "password123"
    
    print("Registering user...")
    response_reg = client.post("/api/auth/register", json={"email": email, "password": password})
    
    if response_reg.status_code == 400 and "already exists" in response_reg.text:
         print("User already exists, proceeding to login...")
    else:
         assert response_reg.status_code == 200, f"Register failed: {response_reg.text}"
         assert "access_token" in response_reg.json()

    # 2. Login
    print("Logging in...")
    response_login = client.post("/api/auth/login", data={"username": email, "password": password})
    assert response_login.status_code == 200, f"Login failed: {response_login.text}"
    token = response_login.json()["access_token"]
    print(f"Got Token: {token[:10]}...")

    # 3. Access Protected Route
    print("Accessing Protected /api/portfolio...")
    headers = {"Authorization": f"Bearer {token}"}
    response_port = client.get("/api/portfolio/", headers=headers)
    assert response_port.status_code == 200, f"Protected route failed: {response_port.text}"
    print("Accessed Protected Route OK!")

    # 4. Add Portfolio Item
    print("Adding Portfolio Item...")
    response_add = client.post("/api/portfolio/", headers=headers, json={
        "ticker": "AAPL",
        "quantity": 5,
        "avg_cost": 150.0
    })
    assert response_add.status_code == 200
    print("Added OK!")

if __name__ == "__main__":
    try:
        test_auth_flow()
        print("\n✅ Auth Flow Verification Passed!")
    except Exception as e:
        print(f"\n❌ Tests Failed: {e}")
        exit(1)
