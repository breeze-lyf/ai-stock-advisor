
import asyncio
import yfinance as yf
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_yf")

async def diagnose_mu():
    ticker = "MU"
    logger.info(f"--- 诊断开始: {ticker} ---")
    
    # 检查环境变量
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    logger.info(f"当前代理设置: {proxy}")
    
    try:
        tick = yf.Ticker(ticker)
        
        # 1. 直接获取 Info (这是最慢也最容易挂的部分)
        logger.info("正在调用 tick.info...")
        info = tick.info
        
        if not info:
            logger.error("tick.info 返回为空！")
        else:
            logger.info(f"Info 获取成功，包含 {len(info)} 个字段")
            # 检查关键字段
            keys_to_check = [
                'shortName', 'sector', 'industry', 'marketCap', 
                'trailingPE', 'forwardPE', 'trailingEps', 
                'dividendYield', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow'
            ]
            for key in keys_to_check:
                logger.info(f"字段 {key}: {info.get(key)}")
                
        # 2. 检查历史价格
        logger.info("正在获取 1d 历史数据...")
        hist = tick.history(period="1d")
        if hist.empty:
            logger.error("历史价格获取失败！")
        else:
            logger.info(f"价格获取成功: {hist['Close'].iloc[-1]}")
            
    except Exception as e:
        logger.error(f"发生异常: {str(e)}")

if __name__ == "__main__":
    asyncio.run(diagnose_mu())
