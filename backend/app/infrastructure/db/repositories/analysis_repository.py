from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.analysis import AnalysisReport
from app.models.portfolio import Portfolio
from app.models.stock import MarketDataCache, Stock, StockNews


class AnalysisRepository:
    SHARED_SCOPE = "shared_stock_analysis"
    USER_INTERACTION_SCOPE = "user_interaction"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_reports_since(self, user_id: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(AnalysisReport).where(
            AnalysisReport.user_id == user_id,
            AnalysisReport.report_scope == self.USER_INTERACTION_SCOPE,
            AnalysisReport.created_at >= since,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_stock(self, ticker: str):
        result = await self.db.execute(select(Stock).where(Stock.ticker == ticker))
        return result.scalar_one_or_none()

    async def get_latest_stock_news(self, ticker: str, limit: int = 5):
        stmt = (
            select(StockNews)
            .where(StockNews.ticker == ticker)
            .order_by(StockNews.publish_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_portfolio_item(self, user_id: str, ticker: str):
        stmt = select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.ticker == ticker)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_report(self, user_id: str, ticker: str):
        stmt = (
            select(AnalysisReport)
            .where(
                AnalysisReport.user_id == user_id,
                AnalysisReport.ticker == ticker,
                AnalysisReport.report_scope == self.USER_INTERACTION_SCOPE,
            )
            .order_by(AnalysisReport.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_reports_for_ticker(self, ticker: str, limit: int = 5, model_used: str | None = None):
        stmt = select(AnalysisReport).where(
            AnalysisReport.ticker == ticker,
            AnalysisReport.report_scope == self.SHARED_SCOPE,
        )
        if model_used:
            stmt = stmt.where(AnalysisReport.model_used == model_used)
        stmt = stmt.order_by(AnalysisReport.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_report_history(self, user_id: str, ticker: str, limit: int):
        stmt = (
            select(AnalysisReport)
            .where(
                AnalysisReport.user_id == user_id,
                AnalysisReport.ticker == ticker,
                AnalysisReport.report_scope == self.USER_INTERACTION_SCOPE,
            )
            .order_by(AnalysisReport.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_report_history_for_ticker(self, ticker: str, limit: int, model_used: str | None = None):
        stmt = select(AnalysisReport).where(
            AnalysisReport.ticker == ticker,
            AnalysisReport.report_scope == self.SHARED_SCOPE,
        )
        if model_used:
            stmt = stmt.where(AnalysisReport.model_used == model_used)
        stmt = stmt.order_by(AnalysisReport.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_market_cache(self, ticker: str):
        result = await self.db.execute(select(MarketDataCache).where(MarketDataCache.ticker == ticker))
        return result.scalar_one_or_none()

    async def add_report(self, report: AnalysisReport):
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def save_market_cache(self, cache: MarketDataCache):
        await self.db.commit()
        await self.db.refresh(cache)
        return cache

    async def rollback(self):
        await self.db.rollback()
