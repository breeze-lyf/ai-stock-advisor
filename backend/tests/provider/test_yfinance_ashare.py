import yfinance as yf
import pandas as pd

def test_yf_a(symbol):
    print(f"\n--- Testing yfinance for: {symbol} ---")
    try:
        tick = yf.Ticker(symbol)
        info = tick.info
        print(f"Name: {info.get('longName')}")
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        print(f"Price: {price}, Currency: {info.get('currency')}")
        
        hist = tick.history(period="5d")
        print("Last 5 days Close prices:")
        print(hist['Close'])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yf_a("002050.SZ")
    test_yf_a("002970.SZ")
    test_yf_a("600519.SS")
