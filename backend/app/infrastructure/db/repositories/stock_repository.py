from __future__ import annotations
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.stock import MarketDataCache, Stock, StockNews


class StockRepository:
    """
    股票基础数据仓储层。
    
    职责：
    - 处理股票代码 (Ticker) 和 名称 (Name) 的模糊搜索。
    - 管理股票基础属性的 CRUD。
    - 支持新闻数据的深度检索。
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, limit: int = 10):
        """
        模糊搜索股票。
        支持根据代码或名称进行不区分大小写的匹配。
        """
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
        """
        原子化添加股票并初始化行情缓存。
        
        【业务逻辑】
        当新标的被引入系统时，必须同步在 `market_data_cache` 表中占位，
        否则后续的实时行情同步任务会因找不到缓存记录而执行失败。
        """
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

