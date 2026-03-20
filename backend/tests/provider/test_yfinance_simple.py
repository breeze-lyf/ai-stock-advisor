import yfinance as yf
import requests
import os
from dotenv import load_dotenv

# 1. 加载环境变量 (获取 .env 中的 HTTP_PROXY)
load_dotenv()

def test_stock_data(ticker_symbol="AAPL"):
    proxy = os.getenv("HTTP_PROXY")
    
    print("=" * 50)
    print(f"🚀 开始测试股票数据抓取: {ticker_symbol}")
    
    # 2. 配置带代理的 Session
    session = requests.Session()
    if proxy:
        print(f"🌐 检测到代理配置: {proxy}")
        session.proxies = {
            "http": proxy,
            "https": proxy
        }
    else:
        print("⚠️ 未检测到代理配置，尝试直连...")

    try:
        # 3. 初始化 Ticker 并获取数据
        stock = yf.Ticker(ticker_symbol, session=session)
        
        # 获取实时基础报价
        info = stock.info
        
        print("-" * 50)
        print(f"✅ 成功连接雅虎金融！")
        print(f"股票全称: {info.get('longName')}")
        print(f"当前价格: ${info.get('currentPrice') or info.get('regularMarketPrice')}")
        print(f"所属行业: {info.get('industry')}")
        print(f"市值: {info.get('marketCap')}")
        
        # 获取最近5天的历史记录
        print("-" * 50)
        print("📊 最近5天历史收盘价:")
        hist = stock.history(period="5d")
        print(hist[['Close']])
        
    except Exception as e:
        print("-" * 50)
        print(f"❌ 获取数据失败！")
        print(f"错误信息: {e}")
        print("\n💡 提示: 如果报错 'Too Many Requests'，请在 Clash 中尝试切换一个节点。")
    
    print("=" * 50)

if __name__ == "__main__":
    # 你可以修改这里的代码来测试不同的股票
    test_stock_data("AAPL")
