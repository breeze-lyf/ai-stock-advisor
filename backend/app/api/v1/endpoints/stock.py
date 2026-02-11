import math
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

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
