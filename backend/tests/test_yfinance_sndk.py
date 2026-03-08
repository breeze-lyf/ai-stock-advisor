import yfinance as yf
import pandas as pd
import json
import math
import sys
import os

# Ensure we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.security import sanitize_float
from app.services.indicators import TechnicalIndicators

ticker = "SNDK"
print(f"--- Fetching data for {ticker} ---")
tick = yf.Ticker(ticker)
info = tick.info
print(f"Name: {info.get('shortName')}")

# Test sanitize_float on info
price = info.get('currentPrice') or info.get('regularMarketPrice')
sanitized_price = sanitize_float(price, 0.0)
print(f"Original Price: {price}, Sanitized: {sanitized_price}")

hist = tick.history(period="1mo", interval="1d")
print("\n--- Calculating indicators ---")
hist_with_ind = TechnicalIndicators.add_historical_indicators(hist)

# Get the latest indicators (which might be NaN)
latest = hist_with_ind.iloc[-1].to_dict()
print("\n--- Latest Raw Indicators ---")
for k, v in latest.items():
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        print(f"{k}: {v} (INVALID)")
    else:
        print(f"{k}: {v}")

print("\n--- Sanitization Test ---")
sanitized_latest = {k: sanitize_float(v) for k, v in latest.items()}
for k, v in sanitized_latest.items():
    if v is None:
        print(f"{k}: {v} (Successfully Cleaned)")
    else:
        print(f"{k}: {v}")
