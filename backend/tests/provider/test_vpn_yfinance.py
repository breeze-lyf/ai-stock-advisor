import yfinance as yf
import os
proxy = 'http://127.0.0.1:7897' # 代理设置，此处修改
os.environ['HTTP_PROXY'] = proxy 
os.environ['HTTPS_PROXY'] = proxy 

train_data =  yf.download("AAPL", start="2026-01-03", end="2026-01-10", interval="1d", auto_adjust=False)
print(train_data.head())
