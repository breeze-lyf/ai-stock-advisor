"""
财经日历 API
提供宏观经济事件、财报发布等日历事件的查询
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.economic_calendar import EconomicCalendarService

router = APIRouter()


@router.get("/economic")
async def get_economic_events(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    country: Optional[str] = Query(None, description="国家/地区 (US, CN, EU 等)"),
    importance: Optional[int] = Query(None, ge=1, le=3, description="重要性等级"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取宏观经济事件日历

    事件类型包括:
    - 央行议息会议 (Federal Reserve, ECB, PBOC 等)
    - 通胀数据 (CPI, PPI)
    - 就业数据 (Non-Farm Payrolls, Unemployment Rate)
    - GDP 数据
    - 其他经济指标
    """
    start = None
    end = None

    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    events = await EconomicCalendarService.get_economic_events(
        db,
        start_date=start,
        end_date=end,
        country=country,
        importance=importance,
        event_type=event_type,
        limit=limit,
    )

    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/economic/high-impact")
async def get_high_impact_events(
    days_ahead: int = Query(7, ge=1, le=30, description="未来天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取未来高影响事件（重要性 3 星）

    高影响事件通常会引起市场显著波动
    """
    events = await EconomicCalendarService.get_high_impact_events(db, days_ahead=days_ahead)

    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/earnings")
async def get_earnings_events(
    tickers: Optional[str] = Query(None, description="股票代码列表，逗号分隔"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取财报发布日历

    可以查询特定股票或日期范围内的财报发布
    """
    ticker_list = None
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]

    start = None
    end = None

    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    events = await EconomicCalendarService.get_earnings_events(
        db,
        tickers=ticker_list,
        start_date=start,
        end_date=end,
        limit=limit,
    )

    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/earnings/portfolio")
async def get_portfolio_earnings(
    days_ahead: int = Query(14, ge=1, le=60, description="未来天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户持仓的财报发布

    自动查询用户持仓股票在未来指定天数内的财报发布
    """
    events = await EconomicCalendarService.get_portfolio_earnings(db, current_user.id, days_ahead=days_ahead)

    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/earnings/mega-cap")
async def get_mega_cap_earnings(
    days_ahead: int = Query(30, ge=1, le=90, description="未来天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取美股七大巨头财报

    七大巨头：AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
    """
    events = await EconomicCalendarService.get_mega_cap_earnings(db, days_ahead=days_ahead)

    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/events/by-country")
async def get_events_by_country(
    countries: str = Query(..., description="国家列表，逗号分隔 (如：US,CN,EU)"),
    days_ahead: int = Query(14, ge=1, le=30, description="未来天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    按国家获取经济事件

    支持同时查询多个国家/地区的事件
    """
    country_list = [c.strip().upper() for c in countries.split(",")]

    events = await EconomicCalendarService.get_events_by_country(db, country_list, days_ahead=days_ahead)

    return {
        "status": "success",
        "countries": country_list,
        "events": events,
    }


@router.get("/alerts")
async def get_user_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的日历提醒设置"""
    alerts = await EconomicCalendarService.get_user_alerts(db, current_user.id)

    return {
        "status": "success",
        "alerts": alerts,
    }


@router.post("/alerts")
async def create_alert(
    alert_type: str = Query(..., description="提醒类型 (economic/earnings)"),
    ticker: Optional[str] = Query(None, description="特定股票代码"),
    country: Optional[str] = Query(None, description="特定国家"),
    importance_min: int = Query(2, ge=1, le=3, description="最小重要性等级"),
    remind_before_minutes: int = Query(30, ge=5, le=1440, description="提前提醒分钟数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建日历提醒"""
    alert = await EconomicCalendarService.create_alert(
        db,
        current_user.id,
        alert_type=alert_type,
        ticker=ticker,
        country=country,
        importance_min=importance_min,
        remind_before_minutes=remind_before_minutes,
    )

    return {
        "status": "success",
        "alert": alert,
    }
