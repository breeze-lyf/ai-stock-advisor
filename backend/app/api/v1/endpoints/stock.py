import math
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf
import pandas as pd
from datetime import datetime
import asyncio
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio
from sqlalchemy.future import select

from app.core.database import get_db
from app.schemas.market_data import OHLCVItem

router = APIRouter()

# 数据清洗器：将无效数值转化为 None。
# 场景：yfinance 抓取的数据有时会出现 NaN (非数字) 或 Inf (无穷大)，
# 这种数据直接传给前端会导致 JSON 解析崩溃，所以需要过滤。
def _sanitize_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

# OHLCV 数据集清洗：批量处理 K 线图所需的数据
def _sanitize_ohlcv(items: list) -> list:
    sanitized = []
    for item in items:
        # 兼容 dict 或 Pydantic 模型
        d = item if isinstance(item, dict) else item.model_dump()
        d["open"] = _sanitize_float(d.get("open")) or 0.0
        d["high"] = _sanitize_float(d.get("high")) or 0.0
        d["low"] = _sanitize_float(d.get("low")) or 0.0
        d["close"] = _sanitize_float(d.get("close")) or 0.0
        d["volume"] = _sanitize_float(d.get("volume"))
        # 清洗附带的技术指标 (RSI/MACD 等)
        for key in ["rsi", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_middle", "bb_lower"]:
            d[key] = _sanitize_float(d.get(key))
        sanitized.append(OHLCVItem(**d))
    return sanitized

@router.get("/{ticker}/history", response_model=List[OHLCVItem])
async def get_stock_history(
    ticker: str,
    period: str = "1y",     # 时间跨度，如 1y (一年), 1mo (一月), 5d (五天)
    interval: str = "1d",   # 频率，如 1d (日线), 1hk (小时线)
    db: AsyncSession = Depends(get_db)
):
    """
    接口：获取股票的历史行情数据，专为 K 线图打造。
    """
    ticker = ticker.upper().strip()
    
    try:
        from app.services.market_providers import ProviderFactory
        
        # 工厂模式：它会根据 Ticker 自动判断去哪抓数据。
        # 比如输入 'AAPL' 会去美股源，输入 '600519.SH' 则会自动切换到 A 股源。
        provider = ProviderFactory.get_provider(ticker)
        data = await provider.get_ohlcv(ticker, interval=interval, period=period)
        
        if not data:
            raise HTTPException(status_code=404, detail="未找到历史 K 线数据。")
        
        return _sanitize_ohlcv(data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行情历史失败: {str(e)}")

@router.post("/refresh_all")
async def refresh_all_stocks(
    db: AsyncSession = Depends(get_db)
):
    """
    接口：一键同步当前数据库中所有活跃股票的最新行情。
    
    机制：使用“信号量 (Semaphore)”控制并发，避免瞬间发起上百个请求被 API 服务商拉黑。
    """
    try:
        # 1. 查询数据库中所有不重复的股票代码
        result = await db.execute(select(Portfolio.ticker).distinct())
        tickers = result.scalars().all()
        
        if not tickers:
            return {"message": "当前没有已关注的股票需要更新。", "updated_count": 0}

        # 2. 并发同步逻辑
        # 我们一次只允许 5 个任务并行，其它的排队等候，这样比较稳健。
        semaphore = asyncio.Semaphore(5)
        
        async def refresh_one(ticker):
            async with semaphore:
                try:
                    # 强制刷新缓存，去调真正的 API。
                    await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
                    return ticker
                except Exception as e:
                    print(f"刷新 {ticker} 失败: {e}")
                    return None

        # 构造所有任务并同步启动
        tasks = [refresh_one(t) for t in tickers]
        results = await asyncio.gather(*tasks)
        
        updated = [t for t in results if t is not None]
        
        return {
            "message": f"成功刷新 {len(updated)} 支股票数据。", 
            "updated_count": len(updated),
            "failed_count": len(tickers) - len(updated)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量刷新任务失败: {str(e)}")
