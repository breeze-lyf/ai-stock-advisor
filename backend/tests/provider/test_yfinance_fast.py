import yfinance as yf
import sys

def test_stock_fast(ticker):
    print(f"Testing {ticker} with fast_info/history...")
    try:
        tick = yf.Ticker(ticker)
        
        # Method 1: fast_info
        try:
            price = tick.fast_info['last_price']
            print(f"fast_info success: {price}")
        except Exception as e:
            print(f"fast_info failed: {e}")
            
        # Method 2: history
        try:
            hist = tick.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                print(f"history success: {price}")
            else:
                print("history empty")
        except Exception as e:
            print(f"history failed: {e}")

    except Exception as e:
        print(f"Main Error: {e}")

if __name__ == "__main__":
    test_stock_fast(sys.argv[1] if len(sys.argv) > 1 else "AAPL")
