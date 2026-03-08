import requests
import os

print("--- Testing Direct East Money API for A-Share (002050) WITHOUT Proxy ---")
# 0.002050 (EM notation for SZ)
url = "https://push2.eastmoney.com/api/qt/stock/get?secid=0.002050&fields=f43,f170,f58"
try:
    resp = requests.get(url, timeout=5, proxies={"http": None, "https": None}, headers={"User-Agent": "Mozilla/5.0"})
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Data: {resp.json()}")
except Exception as e:
    print(f"Failed: {e}")
