"""
选股器 API
提供预设策略和自定义筛选功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.stock_screener import StockScreenerService

router = APIRouter()


@router.get("/presets")
async def get_preset_strategies(
    strategy: str = Query(..., description="策略名称", enum=["low_valuation", "growth", "momentum", "high_dividend"]),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取预设策略选股结果

    策略说明:
    - low_valuation: 低估值策略 (PE<15, PB<2, 股息率>2%)
    - growth: 成长策略 (营收增速>20%, 净利增速>30%, ROE>15%)
    - momentum: 动量策略 (RSI>50, MACD 金叉)
    - high_dividend: 高股息策略 (股息率>5%, PE<20)
    """
    strategies = {
        "low_valuation": StockScreenerService.screen_low_valuation,
        "growth": StockScreenerService.screen_growth,
        "momentum": StockScreenerService.screen_momentum,
        "high_dividend": StockScreenerService.screen_high_dividend,
    }

    screen_func = strategies.get(strategy)
    if not screen_func:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

    results = await screen_func(db, limit=limit)

    return {
        "strategy": strategy,
        "count": len(results),
        "stocks": results,
    }


@router.get("/custom")
async def screen_custom(
    pe_ratio_min: Optional[float] = Query(None, description="PE 最小值"),
    pe_ratio_max: Optional[float] = Query(None, description="PE 最大值"),
    pb_ratio_min: Optional[float] = Query(None, description="PB 最小值"),
    pb_ratio_max: Optional[float] = Query(None, description="PB 最大值"),
    roe_min: Optional[float] = Query(None, description="ROE 最小值"),
    revenue_growth_min: Optional[float] = Query(None, description="营收增速最小值"),
    earnings_growth_min: Optional[float] = Query(None, description="净利增速最小值"),
    dividend_yield_min: Optional[float] = Query(None, description="股息率最小值"),
    market_cap_min: Optional[float] = Query(None, description="市值最小值"),
    market_cap_max: Optional[float] = Query(None, description="市值最大值"),
    sector: Optional[str] = Query(None, description="行业"),
    exchange: Optional[str] = Query(None, description="交易所"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    自定义条件筛选

    所有条件均为可选，支持组合筛选
    """
    filters = {}

    if pe_ratio_min is not None:
        filters["pe_ratio_min"] = pe_ratio_min
    if pe_ratio_max is not None:
        filters["pe_ratio_max"] = pe_ratio_max
    if pb_ratio_min is not None:
        filters["pb_ratio_min"] = pb_ratio_min
    if pb_ratio_max is not None:
        filters["pb_ratio_max"] = pb_ratio_max
    if roe_min is not None:
        filters["roe_min"] = roe_min
    if revenue_growth_min is not None:
        filters["revenue_growth_min"] = revenue_growth_min
    if earnings_growth_min is not None:
        filters["earnings_growth_min"] = earnings_growth_min
    if dividend_yield_min is not None:
        filters["dividend_yield_min"] = dividend_yield_min
    if market_cap_min is not None:
        filters["market_cap_min"] = market_cap_min
    if market_cap_max is not None:
        filters["market_cap_max"] = market_cap_max
    if sector:
        filters["sector"] = sector
    if exchange:
        filters["exchange"] = exchange

    results = await StockScreenerService.screen_custom(db, filters=filters, limit=limit)

    return {
        "filters": filters,
        "count": len(results),
        "stocks": results,
    }


@router.get("/technical")
async def screen_technical(
    rsi_min: Optional[float] = Query(None, ge=0, le=100, description="RSI 最小值"),
    rsi_max: Optional[float] = Query(None, ge=0, le=100, description="RSI 最大值"),
    macd_golden_cross: bool = Query(False, description="MACD 金叉"),
    above_ma20: bool = Query(False, description="股价在 MA20 之上"),
    above_ma50: bool = Query(False, description="股价在 MA50 之上"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    技术面筛选

    支持 RSI、MACD、均线等技术指标筛选
    """
    results = await StockScreenerService.screen_technical(
        db,
        rsi_min=rsi_min,
        rsi_max=rsi_max,
        macd_golden_cross=macd_golden_cross,
        above_ma20=above_ma20,
        above_ma50=above_ma50,
        limit=limit,
    )

    return {
        "filters": {
            "rsi_min": rsi_min,
            "rsi_max": rsi_max,
            "macd_golden_cross": macd_golden_cross,
            "above_ma20": above_ma20,
            "above_ma50": above_ma50,
        },
        "count": len(results),
        "stocks": results,
    }


@router.get("/sectors")
async def get_sectors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有可用的行业列表"""
    sectors = await StockScreenerService.get_available_sectors(db)
    return {"sectors": sectors}


@router.get("/industries")
async def get_industries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有可用的行业细分列表"""
    industries = await StockScreenerService.get_available_industries(db)
    return {"industries": industries}
