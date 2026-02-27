import requests
import json
import traceback

def test_tencent_advanced(ticker="AAPL"):
    print(f"\n--- [Tencent] 深度测试 {ticker} ---")
    # 尝试多种后缀: us, s_pkus, r_us
    urls = [
        f"http://qt.gtimg.cn/q=us{ticker}",
        f"http://qt.gtimg.cn/q=s_pkus{ticker}", # s_pk 通常代表 pre-market
        f"http://qt.gtimg.cn/q=r_us{ticker}"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
            if resp.status_code == 200:
                print(f"URL: {url} -> {resp.text[:100]}...")
            else:
                print(f"URL: {url} -> 失败 {resp.status_code}")
        except Exception as e:
            print(f"URL: {url} -> 错误: {e}")

def test_sina_fixed(ticker="AAPL"):
    print(f"\n--- [Sina] 深度测试 {ticker} ---")
    # 新浪美股代码通常是 gb_aapl (小写)
    url = f"http://hq.sinajs.cn/list=gb_{ticker.lower()}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.sina.com.cn/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            print(f"返回结果: {resp.text}")
        else:
            print(f"失败: {resp.status_code}")
    except Exception as e:
        print(f"错误: {e}")

def test_tencent_web_fixed(ticker="AAPL"):
    print(f"\n--- [Tencent Web] 修复测试 {ticker} ---")
    url = f"https://web.ifzq.gtimg.cn/appstock/app/usstock/get?_var=v_us{ticker}&ticker={ticker}"
    try:
        resp = requests.get(url, timeout=5, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            content = resp.text
            # 找到第一个 {
            start = content.find('{')
            if start != -1:
                json_data = content[start:]
                data = json.loads(json_data)
                root = data.get("data", {}).get(ticker, {})
                qt = root.get("qt", {}).get(ticker, [])
                if qt:
                    print(f"现价: {qt[3]}, 涨跌幅: {qt[32]}%, 更新时间: {qt[30]}")
                    # 检查盘前数据 (在某些特定字段或通过 diff 判断)
                    # 腾讯这个接口如果此时是盘前，qt[3] 通常就是盘前价
                    print(f"完整数组长度: {len(qt)}")
                else:
                    print("未找到 qt 字段")
            else:
                print("非 JSON 格式")
        else:
            print(f"失败: {resp.status_code}")
    except Exception as e:
        print(f"错误: {e}")
        # traceback.print_exc()

if __name__ == "__main__":
    test_tencent_advanced("AAPL")
    test_sina_fixed("AAPL")
    test_tencent_web_fixed("AAPL")
