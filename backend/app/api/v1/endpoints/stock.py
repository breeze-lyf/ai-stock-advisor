from __future__ import annotations
import math
from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from datetime import datetime
import asyncio
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import sanitize_float
from app.schemas.market_data import OHLCVItem
from app.schemas.portfolio import PortfolioItem
from app.infrastructure.db.repositories.stock_repository import StockRepository
from app.services.market_providers.akshare import AkShareProvider
from app.services.market_providers.alpha_vantage import AlphaVantageProvider

router = APIRouter()
logger = logging.getLogger(__name__)

# 数据清洗器：将无效数值转化为 None。
# 场景：yfinance 抓取的数据有时会出现 NaN (非数字) 或 Inf (无穷大)，
# 这种数据直接传给前端会导致 JSON 解析崩溃，所以需要过滤。
def _sanitize_float_local(val):
    return sanitize_float(val)

# OHLCV 数据集清洗：批量处理 K 线图所需的数据
def _sanitize_ohlcv(items: list) -> list:
    sanitized = []
    # 定义所有需要检查并清洗的浮点字段
    float_fields = [
        "open", "high", "low", "close", "volume",
        "rsi", "macd", "macd_signal", "macd_hist", 
        "bb_upper", "bb_middle", "bb_lower"
    ]
    
    for item in items:
        # 兼容 dict 或 Pydantic 模型
        d = item if isinstance(item, dict) else item.model_dump()
        
        # 遍历所有浮点字段进行清洗
        for field in float_fields:
            if field in d:
                # 核心字段 (OHLC) 默认给 0.0，技术指标默认给 None
                default_val = 0.0 if field in ["open", "high", "low", "close"] else None
                d[field] = sanitize_float(d.get(field), default_val)
        
        # 补充：处理可能存在的 ma_5, ma_10 等动态指标
        for key, val in d.items():
            if key.startswith("ma_") or key.endswith("_indicator"):
                d[key] = sanitize_float(val)
                
        sanitized.append(OHLCVItem(**d))
    return sanitized


def _snapshot_to_portfolio_item(ticker: str, cache, stock) -> PortfolioItem:
    return PortfolioItem(
        ticker=ticker,
        name=(stock.name if stock and stock.name else ticker),
        quantity=0.0,
        avg_cost=0.0,
        current_price=sanitize_float(getattr(cache, "current_price", None), 0.0),
        market_value=0.0,
        unrealized_pl=0.0,
        pl_percent=0.0,
        last_updated=getattr(cache, "last_updated", None),
        sector=getattr(stock, "sector", None) if stock else None,
        industry=getattr(stock, "industry", None) if stock else None,
        market_cap=sanitize_float(getattr(stock, "market_cap", None)) if stock else None,
        pe_ratio=sanitize_float(getattr(stock, "pe_ratio", None)) if stock else None,
        forward_pe=sanitize_float(getattr(stock, "forward_pe", None)) if stock else None,
        eps=sanitize_float(getattr(stock, "eps", None)) if stock else None,
        dividend_yield=sanitize_float(getattr(stock, "dividend_yield", None)) if stock else None,
        beta=sanitize_float(getattr(stock, "beta", None)) if stock else None,
        fifty_two_week_high=sanitize_float(getattr(stock, "fifty_two_week_high", None)) if stock else None,
        fifty_two_week_low=sanitize_float(getattr(stock, "fifty_two_week_low", None)) if stock else None,
        pe_percentile=sanitize_float(getattr(cache, "pe_percentile", None)),
        pb_percentile=sanitize_float(getattr(cache, "pb_percentile", None)),
        net_inflow=sanitize_float(getattr(cache, "net_inflow", None)),
        rsi_14=sanitize_float(getattr(cache, "rsi_14", None)),
        ma_20=sanitize_float(getattr(cache, "ma_20", None)),
        ma_50=sanitize_float(getattr(cache, "ma_50", None)),
        ma_200=sanitize_float(getattr(cache, "ma_200", None)),
        macd_val=sanitize_float(getattr(cache, "macd_val", None)),
        macd_signal=sanitize_float(getattr(cache, "macd_signal", None)),
        macd_hist=sanitize_float(getattr(cache, "macd_hist", None)),
        macd_hist_slope=sanitize_float(getattr(cache, "macd_hist_slope", None)),
        macd_cross=getattr(cache, "macd_cross", None),
        macd_is_new_cross=bool(getattr(cache, "macd_is_new_cross", False)),
        bb_upper=sanitize_float(getattr(cache, "bb_upper", None)),
        bb_middle=sanitize_float(getattr(cache, "bb_middle", None)),
        bb_lower=sanitize_float(getattr(cache, "bb_lower", None)),
        atr_14=sanitize_float(getattr(cache, "atr_14", None)),
        k_line=sanitize_float(getattr(cache, "k_line", None)),
        d_line=sanitize_float(getattr(cache, "d_line", None)),
        j_line=sanitize_float(getattr(cache, "j_line", None)),
        volume_ma_20=sanitize_float(getattr(cache, "volume_ma_20", None)),
        volume_ratio=sanitize_float(getattr(cache, "volume_ratio", None)),
        adx_14=sanitize_float(getattr(cache, "adx_14", None)),
        pivot_point=sanitize_float(getattr(cache, "pivot_point", None)),
        resistance_1=sanitize_float(getattr(cache, "resistance_1", None)),
        resistance_2=sanitize_float(getattr(cache, "resistance_2", None)),
        support_1=sanitize_float(getattr(cache, "support_1", None)),
        support_2=sanitize_float(getattr(cache, "support_2", None)),
        risk_reward_ratio=sanitize_float(getattr(cache, "risk_reward_ratio", None)),
        change_percent=sanitize_float(getattr(cache, "change_percent", None), 0.0),
        market_status=getattr(cache, "market_status", None),
    )


@router.get("/{ticker}", response_model=PortfolioItem)
async def get_stock_snapshot(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """
    接口：获取单只股票的详情快照。
    场景：用户通过 URL 直接打开某个不在持仓中的标的时，前端仍需渲染真实详情，而不是伪造 0 值对象。
    """
    ticker = ticker.upper().strip()

    try:
        cache = await MarketDataService.get_real_time_data(ticker, db)
        stock = await StockRepository(db).get_stock(ticker)

        if not cache and not stock:
            raise HTTPException(status_code=404, detail=f"未找到股票: {ticker}")

        return _snapshot_to_portfolio_item(ticker, cache, stock)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票详情失败: {str(e)}")

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
        logger.info(
            "history fetch ticker=%s provider=%s count=%s",
            ticker,
            provider.__class__.__name__,
            len(data) if data else 0,
        )

        # 非 A 股场景：IBKR 常见失败模式是“可用但未连上网关”，此时回退 AkShare 避免前端趋势图空白。
        is_cn = (ticker.isdigit() and len(ticker) == 6) or any(
            suffix in ticker.upper() for suffix in [".SS", ".SZ"]
        )
        if (not data) and (not is_cn) and provider.__class__.__name__ == "IBKRProvider":
            try:
                fallback_provider = AkShareProvider()
                data = await fallback_provider.get_ohlcv(ticker, interval=interval, period=period)
                logger.info(
                    "history fallback ticker=%s provider=%s count=%s",
                    ticker,
                    fallback_provider.__class__.__name__,
                    len(data) if data else 0,
                )
            except Exception:
                data = []

        # 美股二级兜底：AkShare 为空时回退 AlphaVantage（仅在配置了 API Key 时生效）
        if (not data) and (not is_cn):
            try:
                alpha_provider = AlphaVantageProvider()
                data = await alpha_provider.get_ohlcv(ticker, interval=interval, period=period)
                logger.info(
                    "history fallback ticker=%s provider=%s count=%s",
                    ticker,
                    alpha_provider.__class__.__name__,
                    len(data) if data else 0,
                )
            except Exception:
                data = []
        
        if not data:
            # 容错：如果抓取失败，返回空数组 [] 而非 404，防止前端 Axios 抛异常导致白屏
            return []
        
        return _sanitize_ohlcv(data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取行情历史失败: {str(e)}")

@router.post("/refresh_all")
async def refresh_all_stocks(
    price_only: bool = False, # 支持仅刷新价格模式
    db: AsyncSession = Depends(get_db)
):
    """
    接口：一键同步当前数据库中所有活跃股票的最新行情。
    """
    try:
        # 1. 查询数据库中所有不重复的股票代码
        result = await db.execute(select(Portfolio.ticker).distinct())
        tickers = result.scalars().all()
        
        if not tickers:
            return {"message": "当前没有已关注的股票需要更新。", "updated_count": 0}

        # 2. 并发同步逻辑
        semaphore = asyncio.Semaphore(5)
        
        async def refresh_one(ticker):
            async with semaphore:
                from app.core.database import SessionLocal
                async with SessionLocal() as local_db:
                    try:
                        # 传递 price_only 标志
                        await MarketDataService.get_real_time_data(
                            ticker, 
                            local_db, 
                            force_refresh=True, 
                            price_only=price_only
                        )
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
