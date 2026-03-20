import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.application.portfolio.mappers import portfolio_item_from_row, portfolio_summary_from_rows
from app.infrastructure.db.repositories.portfolio_repository import PortfolioRepository
from app.models.user import User
from app.services.market_data import MarketDataService
from app.schemas.portfolio import PortfolioItem, PortfolioSummary

logger = logging.getLogger(__name__)


class GetPortfolioSummaryUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self) -> PortfolioSummary:
        rows = await self.repo.get_summary_rows(self.current_user.id)
        return portfolio_summary_from_rows(rows)


class GetPortfolioUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self, refresh: bool = False, price_only: bool = False) -> list[PortfolioItem]:
        rows = await self.repo.get_portfolio_rows(self.current_user.id)

        if refresh:
            tickers = [portfolio.ticker for portfolio, _, _ in rows]
            if tickers:
                semaphore = asyncio.Semaphore(3)

                async def refresh_single_ticker(ticker_name: str):
                    async with semaphore:
                        async with SessionLocal() as local_session:
                            try:
                                await MarketDataService.get_real_time_data(
                                    ticker_name,
                                    local_session,
                                    preferred_source=self.current_user.preferred_data_source,
                                    force_refresh=True,
                                    price_only=price_only,
                                    user_id=self.current_user.id,
                                )
                            except Exception as exc:
                                logger.error(f"Error refreshing ticker {ticker_name}: {exc}")

                await asyncio.gather(
                    *[refresh_single_ticker(ticker) for ticker in tickers],
                    return_exceptions=True,
                )
                rows = await self.repo.get_portfolio_rows(self.current_user.id)

        return [portfolio_item_from_row(portfolio, market_cache, stock) for portfolio, market_cache, stock in rows]
