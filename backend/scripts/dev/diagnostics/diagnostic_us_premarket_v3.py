import requests
import json
import re

def test_tencent_web_api(ticker="AAPL"):
    print(f"\n--- 测试 Tencent Web API ({ticker}) ---")
    url = f"https://web.ifzq.gtimg.cn/appstock/app/usstock/get?_var=v_us{ticker}&ticker={ticker}"
    try:
        resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            # v_usAAPL={"code":0,"msg":"","data":{"AAPL":{"qt":{"AAPL":["200","\u82f9\u679c","AAPL.OQ","272.95",...
            content = resp.text
            json_str = content[content.find('=')+1:]
            data = json.loads(json_str)
            qt = data.get("data", {}).get(ticker, {}).get("qt", {}).get(ticker, [])
            if len(qt) > 60:
                print(f"代码: {ticker}, 现价: {qt[3]}, 更新时间: {qt[30]}")
                # 检查是否存在盘前字段 (通常在 60 位之后)
                # 腾讯 Web API 通常会返回非常长的数组
                print(f"数据总长度: {len(qt)}")
                # 尝试寻找盘前价 (通常在某些特定下标)
                # print(f"原始快照: {qt}")
            else:
                print("获取到的数据长度不足")
        else:
            print(f"失败: {resp.status_code}")
    except Exception as e:
        print(f"错误: {e}")

def test_netease_with_headers(ticker="AAPL"):
    print(f"\n--- 测试 Netease with Headers ({ticker}) ---")
    url = f"http://api.money.126.net/data/feed/US_{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://money.163.com/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            content = resp.text
            json_str = content[content.find('(')+1 : content.rfind(')')]
            data = json.loads(json_str)
            item = data.get(f"US_{ticker}", {})
            print(f"代码: {ticker}, 现价: {item.get('price')}, 时间: {item.get('time')}")
            if 'preMarket' in item:
                print(f" -> 发现盘前: {item['preMarket']}")
            else:
                print(" -> 未发现盘前字段")
        else:
            print(f"失败: {resp.status_code}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_tencent_web_api("AAPL")
    test_tencent_web_api("TSLA")
    test_netease_with_headers("AAPL")
    test_netease_with_headers("NVDA")
