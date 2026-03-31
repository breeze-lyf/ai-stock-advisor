from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.analysis import AnalysisReport
from app.models.portfolio import Portfolio
from app.models.stock import MarketDataCache, Stock
from app.models.trade import SimulatedTrade, TradeHistoryLog, TradeStatus
from app.models.user import User


class SchedulerRepository:
    SHARED_SCOPE = "shared_stock_analysis"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_open_simulated_trades(self):
        stmt = select(SimulatedTrade).where(SimulatedTrade.status == TradeStatus.OPEN)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_market_cache(self, ticker: str):
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_market_caches(self):
        res = await self.db.execute(select(MarketDataCache))
        return list(res.scalars().all())

    async def get_today_trade_log(self, trade_id: str, today_start: datetime):
        stmt = select(TradeHistoryLog).where(
            TradeHistoryLog.trade_id == trade_id,
            TradeHistoryLog.log_date >= today_start,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    def add_trade_log(self, log: TradeHistoryLog):
        self.db.add(log)

    async def get_users_holding_ticker(self, ticker: str):
        stmt = select(User).join(Portfolio, User.id == Portfolio.user_id).where(Portfolio.ticker == ticker)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_stock_name(self, ticker: str):
        res = await self.db.execute(select(Stock.name).where(Stock.ticker == ticker))
        return res.scalar_one_or_none() or ticker

    async def get_latest_shared_analysis_report(self, ticker: str):
        stmt = (
            select(AnalysisReport)
            .where(
                AnalysisReport.ticker == ticker,
                AnalysisReport.report_scope == self.SHARED_SCOPE,
            )
            .order_by(AnalysisReport.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_portfolio_tickers(self) -> list[str]:
        """返回所有用户持仓中的不重复 ticker 列表"""
        result = await self.db.execute(select(Portfolio.ticker).distinct())
        return [row[0] for row in result.fetchall()]

    async def get_active_hourly_summary_users(self):
        stmt = select(User).join(Portfolio, User.id == Portfolio.user_id).distinct()
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_users_with_portfolios(self):
        stmt = select(User).join(Portfolio, User.id == Portfolio.user_id).distinct()
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_users_with_daily_reports_enabled(self):
        stmt = (
            select(User)
            .join(Portfolio)
            .where(User.feishu_webhook_url != None, User.enable_daily_report == True)
            .distinct()
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_user_portfolios(self, user_id: str):
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def save_changes(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()
