import akshare as ak
import pandas as pd
import requests
import json
import os

# 模拟无代理环境
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

print("--- Testing AkShare US Spot (EM) ---")
try:
    df = ak.stock_us_spot_em()
    print(f"Success! Found {len(df)} US stocks.")
    aapl = df[df['代码'].str.contains('AAPL', na=False)]
    if not aapl.empty:
        print(f"AAPL Quote: {aapl.iloc[0].to_dict()}")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Testing Direct East Money API for US ---")
# 105.AAPL (EM notation for US)
url = "https://push2.eastmoney.com/api/qt/stock/get?secid=105.AAPL&fields=f43,f170,f58"
try:
    resp = requests.get(url, timeout=5)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Data: {resp.json()}")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Testing AkShare US Daily ---")
try:
    df = ak.stock_us_daily(symbol="AAPL")
    print(f"Success! Last row: {df.iloc[-1].to_dict()}")
except Exception as e:
    print(f"Failed: {e}")
