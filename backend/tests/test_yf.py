import yfinance as yf
import sys

def test_stock(ticker):
    print(f"Testing {ticker}...")
    try:
        tick = yf.Ticker(ticker)
        # Try history first as it's often more reliable than .info
        hist = tick.history(period="1d")
        if not hist.empty:
            print(f"History Success: {hist['Close'].iloc[-1]}")
        else:
            print("History returned empty.")
            
        print("Fetching info (this may be blocked/slow)...")
        info = tick.info
        print(f"Info Success: {info.get('currentPrice')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stock(sys.argv[1] if len(sys.argv) > 1 else "AAPL")
