import requests
import os

def test_tencent_us_premarket(tickers=["AAPL", "TSLA", "NVDA"]):
    """
    测试腾讯行情接口对美股盘前数据的抓取
    """
    print(f"--- 正在测试腾讯美股查询 (上海直连) ---")
    
    # 构造腾讯美股代码格式 usTICKER
    symbols = [f"us{t}" for t in tickers]
    url = f"http://qt.gtimg.cn/q={','.join(symbols)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 环境强制禁用代理 (模拟生产环境)
        proxies = {"http": None, "https": None}
        response = requests.get(url, headers=headers, timeout=5, proxies=proxies)
        
        if response.status_code == 200:
            print(f"请求成功! (Status: 200)")
            content = response.text
            parts = content.split(';')
            
            for part in parts:
                if not part.strip() or '=' not in part:
                    continue
                
                # 解析单行数据 v_usAAPL="...~...~..."
                name_part, data_part = part.split('=', 1)
                ticker = name_part.strip().split('_')[-1]
                data = data_part.strip().strip('"').split('~')
                
                if len(data) > 30:
                    name = data[1]           # 中文名称
                    current_price = data[3]  # 当前价 (盘前时段通常是盘前价)
                    prev_close = data[4]    # 昨收
                    open_price = data[5]    # 今开
                    change_val = data[31]   # 涨跌额
                    change_pct = data[32]   # 涨跌幅
                    update_time = data[30]  # 更新时间
                    
                    # 腾讯美股盘前标识通常在第 3 还是第 31 位有变化，或者通过时间判断
                    print(f"\n[股票]: {ticker} ({name})")
                    print(f" -> 当前价格 (含盘前): ${current_price}")
                    print(f" -> 昨收价格: ${prev_close}")
                    print(f" -> 今日开盘: ${open_price}")
                    print(f" -> 涨跌幅度: {change_pct}%")
                    print(f" -> 更新时间: {update_time} (EST)")
                    
                    # 分析是否处于盘前
                    import datetime
                    try:
                        dt = datetime.datetime.strptime(update_time, '%Y%m%d%H%M%S')
                        print(f" -> 状态判断: 正在尝试解析时段...")
                    except:
                        pass
                else:
                    print(f"数据解析失败: {ticker} 数据量不足")
                    
        else:
            print(f"请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"发生异常: {e}")

if __name__ == "__main__":
    # 测试几个热门美股
    test_tencent_us_premarket(["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"])
