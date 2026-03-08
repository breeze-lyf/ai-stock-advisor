import requests
import json

def fetch_source(name, url, parser):
    print(f"\n--- 测试数据源: {name} ---")
    try:
        proxies = {"http": None, "https": None}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5, proxies=proxies)
        if resp.status_code == 200:
            parser(resp.text)
        else:
            print(f"失败: Status {resp.status_code}")
    except Exception as e:
        print(f"错误: {e}")

def parse_tencent(content):
    if '=' not in content: return
    data = content.split('=')[1].strip('"').split('~')
    if len(data) > 30:
        print(f"代码: {data[0]}, 现价: {data[3]}, 昨收: {data[4]}, 涨跌: {data[32]}%, 时间: {data[30]}")
        # 腾讯有些位可能是盘前价，观察数据
        print(f"原始全数据(部分): {data[:10]}")

def parse_netease(content):
    # Netease 返回类似 _ntes_quote_callback({"US_AAPL": {...}});
    try:
        json_str = content[content.find('(')+1 : content.rfind(')')]
        data = json.loads(json_str)
        for k, v in data.items():
            print(f"代码: {k}, 现价: {v.get('price')}, 昨收: {v.get('yestclose')}, 涨跌: {v.get('percent')}%, 时1间: {v.get('time')}")
            # 检查是否有盘前字段
            pre = v.get('preMarket', {})
            if pre:
                print(f" -> 盘前数据: 价格 {pre.get('price')}, 涨跌 {pre.get('percent')}%")
            else:
                print(" -> 未发现显式盘前字段")
    except Exception as e:
        print(f"解析网易失败: {e}")

def parse_sina(content):
    # Sina 格式类似 var hq_str_gb_aapl="...;
    if '=' not in content: return
    data = content.split('=')[1].strip('"').split(',')
    if len(data) > 20:
        # 新浪美股格式: 0名称, 1现价, 2涨跌额, 3涨跌幅, 4时间, 26昨收
        print(f"代码: AAPL, 现价: {data[1]}, 昨收: {data[26]}, 涨跌: {data[2]}%, 时间: {data[4]}")

if __name__ == "__main__":
    ticker = "AAPL"
    
    # 1. 腾讯方式
    fetch_source("Tencent", f"http://qt.gtimg.cn/q=us{ticker}", parse_tencent)
    
    # 2. 网易方式 (常有盘前)
    fetch_source("Netease", f"http://api.money.126.net/data/feed/US_{ticker}", parse_netease)
    
    # 3. 新浪方式
    fetch_source("Sina", f"http://hq.sinajs.cn/list=gb_{ticker.lower()}", parse_sina)
