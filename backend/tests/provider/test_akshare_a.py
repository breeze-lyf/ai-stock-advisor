import akshare as ak
import pandas as pd
import asyncio
import sys
import os
import requests

# Mocking the bypass proxy logic
import threading
_tls = threading.local()
_original_get_environ_proxies = requests.utils.get_environ_proxies

def _patched_get_environ_proxies(*args, **kwargs):
    if getattr(_tls, 'bypass_proxy', False):
        return {}
    return _original_get_environ_proxies(*args, **kwargs)

requests.utils.get_environ_proxies = _patched_get_environ_proxies

async def test_ticker(symbol):
    print(f"\n--- Testing Ticker: {symbol} ---")
    _tls.bypass_proxy = True
    try:
        # Test stock_individual_info_em with specific headers if possible
        # Actually akshare doesn't let us pass headers easily to its internal requests
        # but we can try to see if it works now with bypass_proxy
        print("Fetching stock_individual_info_em...")
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            data = {row['item']: row['value'] for _, row in info_df.iterrows()}
            print(f"Info Name: {data.get('股票简称')}, Latest: {data.get('最新')}, MC: {data.get('总市值')}")
        else:
            print("Info DF is empty or None")
    except Exception as e:
        print(f"Error in stock_individual_info_em: {e}")

    try:
        print("Fetching stock_zh_a_spot_em...")
        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is not None and not spot_df.empty:
            row = spot_df[spot_df['代码'] == symbol]
            if not row.empty:
                target = row.iloc[0]
                print(f"Spot Price: {target.get('最新价')}, Change%: {target.get('涨跌幅')}, Name: {target.get('名称')}")
            else:
                print(f"Symbol {symbol} not found in spot_df")
            print(f"Total stocks in spot_df: {len(spot_df)}")
        else:
            print("Spot DF is empty or None")
    except Exception as e:
        print(f"Error in stock_zh_a_spot_em: {e}")
    _tls.bypass_proxy = False

if __name__ == "__main__":
    tickers = ["002050", "002970", "600519"]
    for t in tickers:
        asyncio.run(test_ticker(t))
