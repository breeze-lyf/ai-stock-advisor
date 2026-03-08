import requests
import os
import json

def test_tencent_kline():
    symbol = "sz002970"
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={symbol},day,,,200,qfq"
    
    # 禁用代理
    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    old_vals = {var: os.environ.get(var) for var in env_vars}
    for var in env_vars: 
        if var in os.environ: del os.environ[var]
        
    try:
        print(f"Testing Tencent K-line: {url}")
        resp = requests.get(url, timeout=5, proxies={'http': None, 'https': None})
        print(f"Status Code: {resp.status_code}")
        
        content = resp.text
        if "=" in content:
            # 腾讯返回的可能是 kline_dayqfq={...} 这种格式
            json_str = content.split("=", 1)[1]
            data = json.loads(json_str)
            
            stock_data = data.get("data", {}).get(symbol, {})
            kline = stock_data.get("day", stock_data.get("qfqday", []))
            
            if kline:
                print(f"Success! Fetched {len(kline)} days of data.")
                print(f"Latest candle: {kline[-1]}")
                # [Date, Open, Close, High, Low, Volume]
            else:
                print("Failed: No kline data in response.")
                print(f"Raw data Keys: {data.get('data', {}).keys()}")
        else:
            print(f"Failed: Unexpected content format: {content[:100]}")
            
    except Exception as e:
        print(f"Tencent K-line Fetch Failed: {e}")
    finally:
        for var, val in old_vals.items():
            if val is not None: os.environ[var] = val

if __name__ == "__main__":
    test_tencent_kline()
