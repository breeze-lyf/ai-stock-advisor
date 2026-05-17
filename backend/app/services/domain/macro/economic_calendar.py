"""
财经日历服务
提供宏观经济事件、财报发布等日历事件的查询和分析
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.models.calendar import EconomicEvent, EarningsEvent, UserCalendarAlert
from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class EconomicCalendarService:
    """
    财经日历服务

    功能：
    1. 宏观经济事件查询
    2. 财报发布日历
    3. 持仓关联提醒
    4. 事件影响分析
    """

    # ==================== 宏观经济事件 ====================

    @staticmethod
    async def get_economic_events(
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
        importance: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取宏观经济事件

        Args:
            start_date: 开始日期
            end_date: 结束日期
            country: 国家/地区（US, CN, EU 等）
            importance: 重要性等级（1-3）
            event_type: 事件类型
            limit: 返回数量限制
        """
        conditions = []

        if start_date:
            conditions.append(EconomicEvent.event_date >= start_date)
        if end_date:
            conditions.append(EconomicEvent.event_date <= end_date)
        if country:
            conditions.append(EconomicEvent.country == country)
        if importance:
            conditions.append(EconomicEvent.importance >= importance)
        if event_type:
            conditions.append(EconomicEvent.event_type == event_type)

        stmt = select(EconomicEvent).where(and_(*conditions)).order_by(EconomicEvent.event_date.asc()).limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()

        return [EconomicCalendarService._event_to_dict(e) for e in events]

    @staticmethod
    async def get_high_impact_events(
        db: AsyncSession,
        days_ahead: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        获取未来高影响事件（重要性 3 星）

        Args:
            days_ahead: 未来天数
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)

        stmt = select(EconomicEvent).where(
            and_(
                EconomicEvent.event_date >= start_date,
                EconomicEvent.event_date <= end_date,
                EconomicEvent.importance == 3,
            )
        ).order_by(EconomicEvent.event_date.asc())

        result = await db.execute(stmt)
        events = result.scalars().all()

        return [EconomicCalendarService._event_to_dict(e) for e in events]

    @staticmethod
    async def get_events_by_country(
        db: AsyncSession,
        countries: List[str],
        days_ahead: int = 14,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        按国家获取经济事件

        Returns:
            {"US": [...], "CN": [...], "EU": [...]}
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)

        result = {}
        for country in countries:
            stmt = select(EconomicEvent).where(
                and_(
                    EconomicEvent.country == country,
                    EconomicEvent.event_date >= start_date,
                    EconomicEvent.event_date <= end_date,
                )
            ).order_by(EconomicEvent.event_date.asc())

            db_result = await db.execute(stmt)
            events = db_result.scalars().all()
            result[country] = [EconomicCalendarService._event_to_dict(e) for e in events]

        return result

    # ==================== 财报事件 ====================

    @staticmethod
    async def get_earnings_events(
        db: AsyncSession,
        tickers: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取财报发布事件

        Args:
            tickers: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
        """
        conditions = []

        if tickers:
            conditions.append(EarningsEvent.ticker.in_(tickers))
        if start_date:
            conditions.append(EarningsEvent.report_date >= start_date)
        if end_date:
            conditions.append(EarningsEvent.report_date <= end_date)

        stmt = select(EarningsEvent).where(and_(*conditions)).order_by(EarningsEvent.report_date.asc()).limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()

        return [EconomicCalendarService._earnings_to_dict(e) for e in events]

    @staticmethod
    async def get_portfolio_earnings(
        db: AsyncSession,
        user_id: str,
        days_ahead: int = 14,
    ) -> List[Dict[str, Any]]:
        """
        获取用户持仓的财报发布

        Args:
            user_id: 用户 ID
            days_ahead: 未来天数
        """
        # 获取用户持仓
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()

        if not holdings:
            return []

        tickers = [h.ticker for h in holdings]
        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)

        return await EconomicCalendarService.get_earnings_events(
            db, tickers=tickers, start_date=start_date, end_date=end_date
        )

    @staticmethod
    async def get_mega_cap_earnings(
        db: AsyncSession,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取巨头公司财报（美股七大巨头）

        美股七大巨头：AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
        """
        mega_cap_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

        start_date = date.today()
        end_date = start_date + timedelta(days=days_ahead)

        return await EconomicCalendarService.get_earnings_events(
            db, tickers=mega_cap_tickers, start_date=start_date, end_date=end_date
        )

    # ==================== 用户提醒 ====================

    @staticmethod
    async def get_user_alerts(
        db: AsyncSession,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """获取用户的日历提醒设置"""
        stmt = select(UserCalendarAlert).where(UserCalendarAlert.user_id == user_id)
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "ticker": a.ticker,
                "country": a.country,
                "importance_min": a.importance_min,
                "remind_before_minutes": a.remind_before_minutes,
                "is_active": a.is_active,
            }
            for a in alerts
        ]

    @staticmethod
    async def create_alert(
        db: AsyncSession,
        user_id: str,
        alert_type: str,
        ticker: Optional[str] = None,
        country: Optional[str] = None,
        importance_min: int = 2,
        remind_before_minutes: int = 30,
    ) -> Dict[str, Any]:
        """创建日历提醒"""
        alert = UserCalendarAlert(
            user_id=user_id,
            alert_type=alert_type,
            ticker=ticker,
            country=country,
            importance_min=importance_min,
            remind_before_minutes=remind_before_minutes,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "ticker": alert.ticker,
            "country": alert.country,
            "importance_min": alert.importance_min,
            "remind_before_minutes": alert.remind_before_minutes,
        }

    # ==================== 工具函数 ====================

    @staticmethod
    def _event_to_dict(event: EconomicEvent) -> Dict[str, Any]:
        """将 EconomicEvent 转换为字典"""
        return {
            "id": event.id,
            "event_name": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "event_time": event.event_time,
            "country": event.country,
            "importance": event.importance,
            "forecast": event.forecast,
            "previous": event.previous,
            "actual": event.actual,
            "impact": event.impact_analysis,
            "affected_sectors": event.affected_sectors,
        }

    @staticmethod
    def _earnings_to_dict(earnings: EarningsEvent) -> Dict[str, Any]:
        """将 EarningsEvent 转换为字典"""
        return {
            "id": earnings.id,
            "ticker": earnings.ticker,
            "company_name": earnings.company_name,
            "report_type": earnings.report_type,
            "fiscal_year": earnings.fiscal_year,
            "quarter": earnings.fiscal_quarter,
            "report_date": earnings.report_date.isoformat() if earnings.report_date else None,
            "report_time": earnings.report_time,
            "eps_estimate": earnings.eps_estimate,
            "eps_actual": earnings.eps_actual,
            "revenue_estimate": earnings.revenue_estimate,
            "revenue_actual": earnings.revenue_actual,
            "market_reaction": earnings.market_reaction,
            "analyst_commentary": earnings.analyst_commentary,
        }


# 全局单例
economic_calendar_service = EconomicCalendarService()
