import yfinance as yf
from requests import Session
import sys

def test_stock_robust(ticker):
    print(f"Testing {ticker} with robust session...")
    session = Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    tick = yf.Ticker(ticker, session=session)
    
    # Method 1: history
    print("Trying history...")
    try:
        hist = tick.history(period="1d")
        if not hist.empty:
            print(f"History Success: {hist['Close'].iloc[-1]}")
        else:
            print("History empty")
    except Exception as e:
        print(f"History failed: {e}")
        
    # Method 2: info
    print("Trying info...")
    try:
        info = tick.info
        print(f"Info Success: {info.get('currentPrice')}")
    except Exception as e:
        print(f"Info failed: {e}")

if __name__ == "__main__":
    test_stock_robust(sys.argv[1] if len(sys.argv) > 1 else "AAPL")
