from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.market_data import OHLCVItem

router = APIRouter()

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
            
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
