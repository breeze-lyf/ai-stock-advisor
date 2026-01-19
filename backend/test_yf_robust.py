import yfinance as yf
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_robust_yfinance():
    proxy = os.getenv("HTTP_PROXY")
    if proxy:
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy
        print(f"🌐 已配置全局代理: {proxy}")
    
    ticker_symbol = "AAPL"

    print(f"🚀 正在尝试以‘强化伪装模式’抓取: {ticker_symbol}...")

    try:
        # 增加超时设置，防止死等
        stock = yf.Ticker(ticker_symbol)
        
        # 换一种获取方式：不直接用 .info (info 接口查得最严)
        # 用 .fast_info 或者 .history 往往更容易通过
        price = stock.fast_info['last_price']
        
        print(f"✅ 抓取成功！")
        print(f"当前价格: ${price:.2f}")
        
    except Exception as e:
        print(f"❌ 依旧失败: {e}")
        print("\n💡 终极分析：这说明雅虎已经封掉了这个节点所在机房的整段 IP。")

if __name__ == "__main__":
    test_robust_yfinance()
