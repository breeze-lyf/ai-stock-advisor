import requests
import json
import os

print("--- Testing Direct East Money API for US (AAPL) WITHOUT Proxy ---")
# 105.AAPL (EM notation for US)
for secid in ["105.AAPL", "106.AAPL", "107.AAPL"]:
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f170,f58"
    try:
        # 强制设置 proxies={} 绕过任何环境变量
        resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
        print(f"ID {secid} -> Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if data and data.get("data"):
                print(f"Success! Data: {data['data']}")
                break
            else:
                print(f"No data field in response: {data}")
    except Exception as e:
        print(f"Failed for {secid}: {e}")

print("\n--- Testing AkShare US Spot (EM) WITHOUT Proxy ---")
import akshare as ak
try:
    # AkShare 内部也使用 requests，我们需要确保它也不用代理
    # 简单的办法是在此进程中清除环境变量
    os.environ['HTTP_PROXY'] = ""
    os.environ['HTTPS_PROXY'] = ""
    os.environ['all_proxy'] = ""
    
    df = ak.stock_us_spot_em()
    print(f"Success! Found {len(df)} US stocks.")
    aapl = df[df['代码'].str.contains('AAPL', na=False)]
    if not aapl.empty:
        print(f"AAPL Quote: {aapl.iloc[0].to_dict()}")
except Exception as e:
    print(f"Failed AkShare: {e}")
