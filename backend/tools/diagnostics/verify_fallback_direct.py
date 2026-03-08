import asyncio
import os
import sys

# 将工程目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 明确清理环境
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
    os.environ.pop(var, None)

from app.services.market_providers.akshare import AkShareProvider

async def verify():
    print("--- Directly Verifying AkShareProvider._get_us_quote WITHOUT Proxy ---")
    provider = AkShareProvider()
    
    # 第一次调用：应该触发 Yahoo 失败（无代理）并回退到 EM
    print("Fetching AAPL...")
    quote = await provider._get_us_quote("AAPL")
    
    if quote:
        print(f"Success! AAPL Price: {quote.price}")
        print(f"Provider Source: East Money (via Fallback)")
    else:
        print("Failed: No quote returned for AAPL.")

    # 第二次调用：应该使用缓存
    print("\nFetching TSLA (should use cache)...")
    quote_tsla = await provider._get_us_quote("TSLA")
    if quote_tsla:
        print(f"Success! TSLA Price: {quote_tsla.price}")
    else:
        print("Failed: No quote returned for TSLA.")

if __name__ == "__main__":
    asyncio.run(verify())
