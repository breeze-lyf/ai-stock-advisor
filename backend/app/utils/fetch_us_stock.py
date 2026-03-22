import sys
import json
import pandas as pd
import akshare as ak
import os

def fetch_us_stock(ticker, end_date=None):
    try:
        # 尝试新浪日线
        # ak.stock_us_daily(symbol=ticker, adjust="qfq") 返回全量历史数据
        df = ak.stock_us_daily(symbol=ticker, adjust="qfq")
        if df is not None and not df.empty:
            if end_date:
                # 过滤在该日期之前的数据
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] < pd.to_datetime(end_date)]
            # 转换为 JSON 记录返回
            return df.to_json(orient="records", date_format="iso")
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    end_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = fetch_us_stock(ticker, end_date)
    print(result)
