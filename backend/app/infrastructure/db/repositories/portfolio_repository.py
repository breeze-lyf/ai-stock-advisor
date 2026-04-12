from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.analysis import PortfolioAnalysisReport
from app.models.portfolio import Portfolio
from app.models.stock import MarketDataCache, Stock, StockNews


class PortfolioRepository:
    """
    持仓组合仓储层。
    
    职责：
    - 处理用户持仓标的 (Portfolio) 与实时行情 (MarketDataCache) 及股票基础信息 (Stock) 的多表联查。
    - 管理持仓资产的增删改查。
    - 持久化 AI 对用户资产组合 (PortfolioAnalysisReport) 的综合诊断结果。
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary_rows(self, user_id: str):
        """
        获取用户持仓汇总数据。
        通过连接 Portfolio (持仓数量) 和 MarketDataCache (现价) 来计算账户总资产。
        """
        stmt = (
            select(Portfolio, MarketDataCache, Stock)
            .outerjoin(MarketDataCache, Portfolio.ticker == MarketDataCache.ticker)
            .outerjoin(Stock, Portfolio.ticker == Stock.ticker)
            .where(Portfolio.user_id == user_id, Portfolio.quantity > 0)
        )
        result = await self.db.execute(stmt)
        return result.all()

    async def get_portfolio_rows(self, user_id: str):
        stmt = (
            select(Portfolio, MarketDataCache, Stock)
            .outerjoin(MarketDataCache, Portfolio.ticker == MarketDataCache.ticker)
            .outerjoin(Stock, Portfolio.ticker == Stock.ticker)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.sort_order.asc(), Portfolio.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return result.all()

    async def get_portfolio_item(self, user_id: str, ticker: str):
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.ticker == ticker)
        )
        return result.scalar_one_or_none()

    async def get_max_sort_order(self, user_id: str) -> int:
        stmt = (
            select(Portfolio.sort_order)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.sort_order.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def get_market_cache(self, ticker: str):
        result = await self.db.execute(select(MarketDataCache).where(MarketDataCache.ticker == ticker))
        return result.scalar_one_or_none()

    async def get_stock_news(self, tickers: list[str], limit: int = 15):
        stmt = (
            select(StockNews)
            .where(StockNews.ticker.in_(tickers))
            .order_by(StockNews.publish_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def add_portfolio_item(self, item: Portfolio):
        self.db.add(item)

    async def delete_portfolio_item(self, item: Portfolio):
        await self.db.delete(item)

    async def save_changes(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()

    async def latest_portfolio_analysis(self, user_id: str):
        stmt = (
            select(PortfolioAnalysisReport)
            .where(PortfolioAnalysisReport.user_id == user_id)
            .order_by(PortfolioAnalysisReport.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_portfolio_analysis(self, report: PortfolioAnalysisReport):
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
