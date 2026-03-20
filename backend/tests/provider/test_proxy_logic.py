import requests
import os
import threading
import requests.utils

_tls = threading.local()
_original_get_environ_proxies = requests.utils.get_environ_proxies

def _patched_get_environ_proxies(*args, **kwargs):
    if getattr(_tls, 'bypass_proxy', False):
        print("Patch triggered: returning {}")
        return {}
    return _original_get_environ_proxies(*args, **kwargs)

requests.utils.get_environ_proxies = _patched_get_environ_proxies

def test():
    # 模拟环境变量
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
    
    print("\n--- Test 1: Patch + Environment masking ---")
    _tls.bypass_proxy = True
    old_proxies = {var: os.environ.get(var) for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']}
    for var in old_proxies:
        if var in os.environ: del os.environ[var]
    
    try:
        # 即使删除了环境变量，看看 requests.Session() 是否还会抓到系统的（macOS 可能有系统级代理设置）
        resp = requests.get("https://www.baidu.com", timeout=2)
        print(f"Success 1: Status {resp.status_code}")
    except Exception as e:
        print(f"Failed 1: {e}")
    finally:
        for var, val in old_proxies.items():
            if val: os.environ[var] = val

    print("\n--- Test 2: Explicit proxies={'http': None, 'https': None} ---")
    try:
        # 直接显式传递，这是最终方案
        resp = requests.get("https://www.baidu.com", timeout=2, proxies={'http': None, 'https': None})
        print(f"Success 2: Status {resp.status_code}")
    except Exception as e:
        print(f"Failed 2: {e}")

if __name__ == "__main__":
    test()
