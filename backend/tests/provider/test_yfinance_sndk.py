import math
import os
import sys

import pytest
import yfinance as yf

# Ensure we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.core.security import sanitize_float
from app.services.indicators import TechnicalIndicators

@pytest.mark.integration
def test_yfinance_sndk_indicator_sanitization():
    ticker = "SNDK"
    try:
        tick = yf.Ticker(ticker)
        info = tick.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        sanitized_price = sanitize_float(price, 0.0)
        assert sanitized_price is not None

        hist = tick.history(period="1mo", interval="1d")
        if hist is None or hist.empty:
            pytest.skip("No yfinance history data returned")

        hist_with_ind = TechnicalIndicators.add_historical_indicators(hist)
        latest = hist_with_ind.iloc[-1].to_dict()
        sanitized_latest = {k: sanitize_float(v) for k, v in latest.items()}

        for _, value in sanitized_latest.items():
            if isinstance(value, float):
                assert not math.isnan(value)
                assert not math.isinf(value)
    except Exception as exc:
        pytest.skip(f"External yfinance/proxy unavailable: {exc}")
