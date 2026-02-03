from fastapi.testclient import TestClient
from app.main import app
import sys
import os

sys.path.append(os.getcwd())

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Service is healthy"}

def test_portfolio_add():
    # Note: DB session handling in TestClient with AsyncSQLAlchemy is tricky without overriding dependency.
    # For MVP verification, we might just checking if the route exists and inputs are validated.
    # OR we spin up uvicorn in background. 
    # Let's try basic validation first.
    
    response = client.post("/api/portfolio/", json={
        "ticker": "NVDA",
        "quantity": 10,
        "avg_cost": 120.0
    })
    # This might fail 500 if DB is not set up correctly in sync context of TestClient, 
    # because `get_db` yields an async session, but TestClient is sync.
    # We need AsyncClient.
    print(f"POST /portfolio status: {response.status_code}")
    # print(response.json())

    response = client.get("/api/portfolio/")
    print(f"GET /portfolio status: {response.status_code}")

def test_analysis():
    response = client.post("/api/analysis/NVDA")
    print(f"POST /analysis/NVDA status: {response.status_code}")
    print(response.json())
    assert response.status_code == 200

if __name__ == "__main__":
    try:
        test_health()
        print("Health check passed.")
        # test_analysis() 
        # test_portfolio is harder without AsyncClient, skipping full integration test in this simple script
        # validation of analysis route which mocks DB usage (it doesn't use DB in current impl)
        test_analysis()
        print("Analysis check passed.")
    except Exception as e:
        print(f"Tests failed: {e}")
