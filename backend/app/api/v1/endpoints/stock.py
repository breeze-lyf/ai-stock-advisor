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

def _sanitize_float(val):
    """将 NaN/Inf 替换为 None，防止 JSON 序列化失败"""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

def _sanitize_ohlcv(items: list) -> list:
    """清洗 OHLCV 列表中的所有浮点字段"""
    sanitized = []
    for item in items:
        d = item if isinstance(item, dict) else item.model_dump()
        d["open"] = _sanitize_float(d.get("open")) or 0.0
        d["high"] = _sanitize_float(d.get("high")) or 0.0
        d["low"] = _sanitize_float(d.get("low")) or 0.0
        d["close"] = _sanitize_float(d.get("close")) or 0.0
        d["volume"] = _sanitize_float(d.get("volume"))
        # 技术指标允许为 None
        for key in ["rsi", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_middle", "bb_lower"]:
            d[key] = _sanitize_float(d.get(key))
        sanitized.append(OHLCVItem(**d))
    return sanitized

@router.get("/{ticker}/history", response_model=List[OHLCVItem])
async def get_stock_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票历史数据用于 K 线图展示
    """
    ticker = ticker.upper().strip()
    
    try:
        from app.services.market_providers import ProviderFactory
        
        # 使用工厂模式自动获取对应的提供商 (美股用 YFinance, A股用 AkShare)
        provider = ProviderFactory.get_provider(ticker)
        data = await provider.get_ohlcv(ticker, interval=interval, period=period)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No history data found for {ticker}")
        
        # 清洗 NaN/Inf 值，防止 JSON 序列化失败
        return _sanitize_ohlcv(data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.post("/refresh_all")
async def refresh_all_stocks(
    db: AsyncSession = Depends(get_db)
):
    """
    强制刷新当前用户持仓列表中的所有股票数据
    """
    try:
        # 1. 获取所有投资组合中的唯一 Ticker
        result = await db.execute(select(Portfolio.ticker).distinct())
        tickers = result.scalars().all()
        
        if not tickers:
            return {"message": "No stocks in portfolio to refresh", "updated_count": 0}

        # 2. 并发触发强制刷新
        # 使用 asyncio.gather 并行处理，MarketDataService 内部已有并发控制
        # 限制并发数为 5 以防对 yfinance/akshare 发起过多请求被封禁
        semaphore = asyncio.Semaphore(5)
        
        async def refresh_one(ticker):
            async with semaphore:
                try:
                    await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
                    return ticker
                except Exception as e:
                    print(f"Failed to refresh {ticker}: {e}")
                    return None

        # 创建任务列表
        tasks = [refresh_one(t) for t in tickers]
        results = await asyncio.gather(*tasks)
        
        updated = [t for t in results if t is not None]
        
        return {
            "message": f"Successfully refreshed {len(updated)} stocks", 
            "updated_count": len(updated),
            "failed_count": len(tickers) - len(updated)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch refresh failed: {str(e)}")
