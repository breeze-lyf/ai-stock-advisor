import requests
import os
import sys

def test_connectivity():
    # 测试东方财富 API
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f12&fs=m:0+t:6&fields=f12,f14,f2"
    
    # 模拟 AkShareProvider 中的禁用代理逻辑
    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    old_vals = {var: os.environ.get(var) for var in env_vars}
    for var in env_vars: 
        if var in os.environ:
            del os.environ[var]
            
    print("--- Diagnostic Report ---")
    print(f"Server OS: {sys.platform}")
    
    try:
        print(f"Testing direct GET to EastMoney: {url}")
        # 尝试不带 headers
        resp = requests.get(url, timeout=5, proxies={'http': None, 'https': None})
        print(f"HTTPS No-headers Result: {resp.status_code}")
    except Exception as e:
        print(f"HTTPS No-headers Failed: {e}")

    # 关键测试：尝试将 HTTPS 改为 HTTP
    try:
        http_url = url.replace("https://", "http://")
        print(f"\nTesting HTTP fallback for EastMoney: {http_url}")
        resp_http = requests.get(http_url, timeout=5, proxies={'http': None, 'https': None})
        print(f"HTTP Result: {resp_http.status_code}")
        if resp_http.status_code == 200:
            print("HTTP IS WORKING!")
    except Exception as e:
        print(f"HTTP Failed: {e}")

    # 尝试模拟更真实的浏览器 Session
    try:
        print("\nTesting Session with realistic headers:")
        session = requests.Session()
        session.trust_env = False
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
        resp4 = session.get(url, timeout=5, headers=headers)
        print(f"Session HTTPS Result: {resp4.status_code}")
    except Exception as e:
        print(f"Session HTTPS Failed: {e}")

    # 测试新浪 API
    try:
        sina_url = "http://hq.sinajs.cn/list=sz000001"
        print(f"\nTesting direct GET to Sina: {sina_url}")
        resp3 = requests.get(sina_url, timeout=5, headers={"Referer": "http://finance.sina.com.cn"}, proxies={'http': None, 'https': None})
        print(f"Sina Result: {resp3.status_code}")
        print(f"Sina Content Length: {len(resp3.text)}")
    except Exception as e:
        print(f"Sina Fetch Failed: {type(e).__name__} - {e}")

    # 还原环境
    for var, val in old_vals.items():
        if val is not None: os.environ[var] = val

if __name__ == "__main__":
    test_connectivity()
