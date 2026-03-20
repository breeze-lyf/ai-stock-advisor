
import httpx
import asyncio
import os
import sys
from dotenv import load_dotenv

# 加载 .env
load_dotenv(dotenv_path="backend/.env")

async def test_siliconflow():
    api_key = os.getenv("SILICONFLOW_API_KEY")
    proxy = os.getenv("HTTP_PROXY")
    
    print(f"Testing SiliconFlow with API Key: {api_key[:10]}...")
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-ai/DeepSeek-V3", # 使用硅基流动的 ID
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "stream": False,
        "temperature": 0.3
    }
    
    print("\n--- Test 1: WITHOUT Proxy ---")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success!")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception without proxy: {str(e)}")

    if proxy:
        print(f"\n--- Test 2: WITH Proxy ({proxy}) ---")
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    print("Success!")
                else:
                    print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception with proxy: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_siliconflow())
