import asyncio
import os
import sys
import httpx

# 验证 API 容错逻辑
async def test_api_tolerance():
    url = "http://localhost:8000/api/portfolio/002050/refresh"
    headers = {
        "Authorization": f"Bearer {os.environ.get('API_TOKEN', 'YOUR_TOKEN_HERE')}"
    }
    
    print(f"Testing refresh API: {url}")
    try:
        async with httpx.AsyncClient() as client:
            # 这里的目的是观察即使在后端日志报 'Connection aborted' 时，返回的状态码是否为 200 或业务错误
            resp = await client.post(url, headers=headers, timeout=20.0)
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # 仅作为逻辑参考，实际运行需要正确的 token
    # asyncio.run(test_api_tolerance())
    print("Script ready for manual trigger or internal logic verification.")
