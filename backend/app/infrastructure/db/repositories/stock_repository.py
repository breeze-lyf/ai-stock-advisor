from __future__ import annotations
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.stock import MarketDataCache, Stock, StockNews


class StockRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, limit: int = 10):
        search_term = f"%{query}%"
        stmt = select(Stock).where(
            or_(
                Stock.ticker.ilike(search_term),
                Stock.name.ilike(search_term),
            )
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_stock(self, ticker: str):
        result = await self.db.execute(select(Stock).where(Stock.ticker == ticker))
        return result.scalar_one_or_none()

    async def add_stock_with_cache(self, ticker: str, name: str, current_price: float | None = None):
        stock = Stock(ticker=ticker, name=name)
        self.db.add(stock)
        self.db.add(MarketDataCache(ticker=ticker, current_price=current_price))
        await self.db.commit()
        return stock

    async def get_latest_news(self, ticker: str, limit: int = 20):
        stmt = (
            select(StockNews)
            .where(StockNews.ticker == ticker)
            .order_by(StockNews.publish_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

