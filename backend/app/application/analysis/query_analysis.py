import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analysis.helpers import (
    extract_entry_prices_fallback,
    extract_entry_zone_fallback,
)
from app.application.analysis.mappers import serialize_analysis_report
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.models.user import User

logger = logging.getLogger(__name__)


class GetLatestAnalysisUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def execute(self, ticker: str) -> dict:
        report = await self.repo.get_latest_report(self.current_user.id, ticker)
        if not report:
            raise HTTPException(status_code=404, detail="No analysis found for this stock and model")

        cache_data = await self.repo.get_market_cache(ticker)
        realtime_rr = None
        if cache_data and cache_data.risk_reward_ratio is not None:
            realtime_rr = f"{cache_data.risk_reward_ratio:.2f}"

        return serialize_analysis_report(report, rr_ratio=realtime_rr)


class GetAnalysisHistoryUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def execute(self, ticker: str, limit: int = 20) -> list[dict]:
        try:
            reports = await self.repo.get_report_history(self.current_user.id, ticker, limit)
            response = []
            for report in reports:
                snapshot = report.input_context_snapshot or {}
                market_data_snap = snapshot.get("market_data", {}) if isinstance(snapshot, dict) else {}
                snap_price = market_data_snap.get("current_price") if isinstance(market_data_snap, dict) else None
                response.append(serialize_analysis_report(report, history_price=snap_price))
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error in get_analysis_history: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")
