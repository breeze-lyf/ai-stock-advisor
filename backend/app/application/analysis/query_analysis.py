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


def _is_error_report(report) -> bool:
    raw = (getattr(report, "ai_response_markdown", None) or "").strip()
    return raw.startswith("**Error**")


class GetLatestAnalysisUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def execute(self, ticker: str) -> dict:
        """
        获取单只股票的最新研判报告。
        
        【查询逻辑】
        1. 优先获取该用户偏好模型（如 DeepSeek-R1）生成的最新“共用范围”报告。
        2. 若偏好模型无数据，逻辑回退至查询该股票的“任意模型”生成的最新有效报告。
        3. 同步提取实时盈亏比（RRR）缓存以保证前端展示的实时性。
        """
        report = await self._get_latest_shared_report(ticker)
        if not report:
            raise HTTPException(status_code=404, detail="No analysis found for this stock and model")

        cache_data = await self.repo.get_market_cache(ticker)
        realtime_rr = None
        if cache_data and cache_data.risk_reward_ratio is not None:
            realtime_rr = f"{cache_data.risk_reward_ratio:.2f}"

        return serialize_analysis_report(report, rr_ratio=realtime_rr)

    async def _get_latest_shared_report(self, ticker: str):
        preferred_model = self.current_user.preferred_ai_model or None
        candidates = await self.repo.get_latest_reports_for_ticker(ticker, limit=10, model_used=preferred_model)
        report = self._pick_shared_scope_report(candidates)
        if report:
            return report

        if preferred_model:
            fallback_candidates = await self.repo.get_latest_reports_for_ticker(ticker, limit=10)
            return self._pick_shared_scope_report(fallback_candidates)

        return None

    @staticmethod
    def _pick_shared_scope_report(reports):
        """
        从候选报告列表中筛选最优的“共享范围”报告。
        
        过滤逻辑：
        - 必须标记为 SHARED_SCOPE。
        - 排除包含 "**Error**" 字样的 AI 报错记录。
        """
        first_shared = None
        for report in reports:
            if getattr(report, "report_scope", None) == AnalysisRepository.SHARED_SCOPE:
                if first_shared is None:
                    first_shared = report
                if not _is_error_report(report):
                    return report
                continue

            snapshot = report.input_context_snapshot or {}
            if isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared":
                if first_shared is None:
                    first_shared = report
                if not _is_error_report(report):
                    return report
        return first_shared


class GetAnalysisHistoryUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def execute(self, ticker: str, limit: int = 20) -> list[dict]:
        try:
            preferred_model = self.current_user.preferred_ai_model or None
            reports = await self.repo.get_report_history_for_ticker(ticker, limit * 3, model_used=preferred_model)
            shared_reports = []
            for report in reports:
                if getattr(report, "report_scope", None) == AnalysisRepository.SHARED_SCOPE:
                    if not _is_error_report(report):
                        shared_reports.append(report)
                else:
                    snapshot = report.input_context_snapshot or {}
                    if isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared":
                        if not _is_error_report(report):
                            shared_reports.append(report)
                if len(shared_reports) >= limit:
                    break

            if not shared_reports and preferred_model:
                fallback_reports = await self.repo.get_report_history_for_ticker(ticker, limit * 3)
                for report in fallback_reports:
                    if getattr(report, "report_scope", None) == AnalysisRepository.SHARED_SCOPE:
                        if not _is_error_report(report):
                            shared_reports.append(report)
                    else:
                        snapshot = report.input_context_snapshot or {}
                        if isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared":
                            if not _is_error_report(report):
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
