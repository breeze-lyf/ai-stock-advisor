import logging
import re
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.infrastructure.db.repositories.portfolio_repository import PortfolioRepository
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate
from app.services.market_data import MarketDataService
from app.services.market_data_persistence import MarketDataPersistence
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


async def background_fetch(ticker: str):
    source = "AKSHARE" if re.match(r"^\d{6}$", ticker) else "YFINANCE"
    async with SessionLocal() as db:
        try:
            await MarketDataService.get_real_time_data(ticker, db, preferred_source=source, force_refresh=True)
            logger.info(f"✅ Background fetch for {ticker} completed (source: {source})")
        except Exception as exc:
            logger.error(f"❌ Background fetch for {ticker} failed: {exc}")


class AddPortfolioItemUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self, item: PortfolioCreate, background_tasks: BackgroundTasks) -> dict:
        ticker = item.ticker.upper().strip()
        existing = await self.repo.get_portfolio_item(self.current_user.id, ticker)

        if existing:
            existing.quantity = item.quantity
            existing.avg_cost = item.avg_cost
        else:
            max_order = await self.repo.get_max_sort_order(self.current_user.id)
            await self.repo.add_portfolio_item(
                Portfolio(
                    user_id=self.current_user.id,
                    ticker=ticker,
                    quantity=item.quantity,
                    avg_cost=item.avg_cost,
                    sort_order=max_order + 1,
                )
            )

        await self.repo.save_changes()
        cache = await self.repo.get_market_cache(ticker)

        needs_fetch = (
            not cache
            or cache.rsi_14 is None
            or (utc_now_naive() - cache.last_updated if cache and cache.last_updated else timedelta(days=1))
            > timedelta(minutes=30)
        )
        if needs_fetch:
            background_tasks.add_task(background_fetch, ticker)

        return {"message": "Portfolio updated", "ticker": ticker, "needs_fetch": needs_fetch}


class DeletePortfolioItemUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self, ticker: str) -> dict:
        item = await self.repo.get_portfolio_item(self.current_user.id, ticker)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        await self.repo.delete_portfolio_item(item)
        await self.repo.save_changes()
        return {"message": "Item deleted"}


class RefreshPortfolioStockUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(
        self,
        ticker: str,
        background_tasks: BackgroundTasks,
        price_only: bool = False,
    ) -> dict:
        ticker = ticker.upper().strip()

        try:
            data = await MarketDataService.fetch_market_data(
                ticker,
                self.current_user.preferred_data_source,
                price_only=price_only,
                db=self.db,
                user_id=self.current_user.id,
            )

            if not data or not data.quote:
                cache = await self.repo.get_market_cache(ticker)

                if cache:
                    return {
                        "ticker": ticker,
                        "success": False,
                        "message": "实时刷新失败（可能受频率限制），已显示最近一次成功抓取的缓存数据。",
                        "current_price": cache.current_price,
                        "change_percent": cache.change_percent,
                        "last_updated": cache.last_updated,
                    }

                return {
                    "ticker": ticker,
                    "success": False,
                    "message": "刷新失败且数据库无历史记录。请稍后再试。",
                }

            if not price_only:
                existing_cache = await self.repo.get_market_cache(ticker)
                await MarketDataService.persist_market_data(
                    ticker,
                    data,
                    existing_cache,
                    self.db,
                    utc_now_naive(),
                )
                cache = await self.repo.get_market_cache(ticker)

                return {
                    "ticker": ticker,
                    "success": True,
                    "message": "深度刷新成功",
                    "current_price": cache.current_price if cache else data.quote.price,
                    "change_percent": cache.change_percent if cache else data.quote.change_percent,
                    "has_indicators": cache.rsi_14 is not None if cache else False,
                }

            background_tasks.add_task(self._background_sync, ticker, data)
            return {
                "ticker": ticker,
                "success": True,
                "message": "行情刷新已排队",
                "current_price": data.quote.price,
                "change_percent": data.quote.change_percent,
            }
        except Exception as exc:
            logger.error(f"Refresh failed for {ticker}: {exc}")
            return {
                "ticker": ticker,
                "success": False,
                "message": f"服务器内部错误: {str(exc)}",
            }

    async def _background_sync(self, ticker: str, data):
        async with SessionLocal() as bg_db:
            try:
                existing_cache = await MarketDataPersistence.get_market_cache(bg_db, ticker)
                await MarketDataService.persist_market_data(ticker, data, existing_cache, bg_db, utc_now_naive())
            except Exception as exc:
                logger.error(f"Background DB sync failed for {ticker}: {exc}")


class ReorderPortfolioUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self, orders: list[dict]) -> dict:
        for item in orders:
            ticker = item.get("ticker")
            new_order = item.get("sort_order")
            if ticker is None or new_order is None:
                continue

            portfolio = await self.repo.get_portfolio_item(self.current_user.id, ticker)
            if portfolio:
                portfolio.sort_order = new_order

        await self.repo.save_changes()
        return {"message": "Reorder successful"}
