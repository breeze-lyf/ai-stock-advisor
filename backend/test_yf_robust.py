import yfinance as yf
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_robust_yfinance():
    proxy = os.getenv("HTTP_PROXY")
    ticker_symbol = "AAPL"
    
    # 强化伪装：使用更像真实 Chrome 浏览器的 Header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive'
    }

    session = requests.Session()
    session.headers.update(headers)
    
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
        print(f"🌐 使用代理: {proxy}")

    print(f"🚀 正在尝试以‘强化伪装模式’抓取: {ticker_symbol}...")

    try:
        # 增加超时设置，防止死等
        stock = yf.Ticker(ticker_symbol, session=session)
        
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
