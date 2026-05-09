import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analysis.helpers import (
    find_latest_shared_report,
    is_error_report,
)
from app.application.analysis.mappers import serialize_analysis_report
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.models.user import User

logger = logging.getLogger(__name__)


class GetLatestAnalysisUseCase:
    def __init__(
        self,
        db: AsyncSession,
        current_user: User,
        analysis_repo: Optional[AnalysisRepository] = None,
    ):
        self.db = db
        self.current_user = current_user
        self.repo = analysis_repo or AnalysisRepository(db)

    async def execute(self, ticker: str) -> dict:
        report = await find_latest_shared_report(
            self.repo, ticker, self.current_user.preferred_ai_model
        )
        if not report:
            raise HTTPException(status_code=404, detail="No analysis found for this stock and model")

        cache_data = await self.repo.get_market_cache(ticker)
        realtime_rr = None
        if cache_data and cache_data.risk_reward_ratio is not None:
            realtime_rr = f"{cache_data.risk_reward_ratio:.2f}"

        return serialize_analysis_report(report, rr_ratio=realtime_rr)


class GetAnalysisHistoryUseCase:
    def __init__(
        self,
        db: AsyncSession,
        current_user: User,
        analysis_repo: Optional[AnalysisRepository] = None,
    ):
        self.db = db
        self.current_user = current_user
        self.repo = analysis_repo or AnalysisRepository(db)

    async def execute(self, ticker: str, limit: int = 20) -> list[dict]:
        try:
            preferred_model = self.current_user.preferred_ai_model or None
            reports = await self.repo.get_report_history_for_ticker(ticker, limit * 3, model_used=preferred_model)
            shared_reports = []
            for report in reports:
                scope = getattr(report, "report_scope", None)
                is_shared = scope == AnalysisRepository.SHARED_SCOPE
                if not is_shared:
                    snapshot = report.input_context_snapshot or {}
                    is_shared = isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared"
                if is_shared and not is_error_report(report):
                    shared_reports.append(report)
                    if len(shared_reports) >= limit:
                        break

            if not shared_reports and preferred_model:
                fallback_reports = await self.repo.get_report_history_for_ticker(ticker, limit * 3)
                for report in fallback_reports:
                    scope = getattr(report, "report_scope", None)
                    is_shared = scope == AnalysisRepository.SHARED_SCOPE
                    if not is_shared:
                        snapshot = report.input_context_snapshot or {}
                        is_shared = isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared"
                    if is_shared and not is_error_report(report):
                        shared_reports.append(report)
                        if len(shared_reports) >= limit:
                            break

            response = []
            for report in shared_reports:
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
