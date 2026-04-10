import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import sanitize_float
from app.application.portfolio.query_portfolio import GetPortfolioSummaryUseCase
from app.infrastructure.db.repositories.portfolio_repository import PortfolioRepository
from app.models.analysis import PortfolioAnalysisReport
from app.models.user import User
from app.schemas.analysis import PortfolioAnalysisResponse
from app.services.ai_service import AIService
from app.services.macro_service import MacroService
from app.services.market_data import MarketDataService
from app.utils.ai_response_parser import parse_portfolio_ai_json
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class AnalyzePortfolioUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self) -> PortfolioAnalysisResponse:
        summary = await GetPortfolioSummaryUseCase(self.db, self.current_user).execute()
        if not summary.holdings:
            raise HTTPException(status_code=400, detail="暂无持仓标的，无法进行组合分析。")

        holdings_data = self._build_holdings_data(summary.holdings)
        market_news_context = await self._build_market_news_context(summary.holdings)
        macro_context = await self._build_macro_context()
        preferred_model = self.current_user.preferred_ai_model or settings.DEFAULT_AI_MODEL

        ai_raw_response = await AIService.generate_portfolio_analysis(
            portfolio_items=holdings_data,
            market_news=market_news_context,
            macro_context=macro_context,
            model=preferred_model,
            db=self.db,
            user_id=self.current_user.id,
        )
        logger.info(f"AI Portfolio Analysis Response: {ai_raw_response[:500]}...")

        # If the AI call failed, raise immediately — don't persist garbage data
        if ai_raw_response.startswith("**Error**") or (
            ai_raw_response.startswith('{"error"') or '"error"' in ai_raw_response[:50]
        ):
            logger.error(f"AI portfolio analysis failed: {ai_raw_response[:200]}")
            raise HTTPException(
                status_code=503,
                detail=f"AI 分析服务暂时不可用，请稍后重试。原因：{ai_raw_response[:200]}",
            )

        parsed_data = parse_portfolio_ai_json(ai_raw_response)
        new_portfolio_report = await self._persist_report(parsed_data, ai_raw_response, preferred_model)

        return PortfolioAnalysisResponse(
            health_score=int(parsed_data.get("health_score", 50)),
            risk_level=str(parsed_data.get("risk_level", "中")),
            summary=str(parsed_data.get("summary", "投资组合概览")),
            diversification_analysis=str(parsed_data.get("diversification_analysis", "分散度分析见详细报告")),
            strategic_advice=str(parsed_data.get("strategic_advice", "保持关注")),
            top_risks=parsed_data.get("top_risks", []),
            top_opportunities=parsed_data.get("top_opportunities", []),
            detailed_report=str(parsed_data.get("detailed_report", ai_raw_response)),
            model_used=preferred_model,
            created_at=new_portfolio_report.created_at if new_portfolio_report else utc_now_naive(),
        )

    def _build_holdings_data(self, holdings: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "ticker": holding.ticker,
                "name": holding.name,
                "market_value": sanitize_float(holding.market_value, 0.0),
                "pl_percent": sanitize_float(holding.pl_percent, 0.0),
                "sector": holding.sector,
                "rrr": sanitize_float(holding.risk_reward_ratio),
                "pe_percentile": getattr(holding, "pe_percentile", None),
                "pb_percentile": getattr(holding, "pb_percentile", None),
                "net_inflow": getattr(holding, "net_inflow", None),
            }
            for holding in holdings
        ]

    async def _build_market_news_context(self, holdings: list[Any]) -> str:
        market_news_context = ""
        try:
            macro_ticker = "^GSPC"
            await MarketDataService.get_real_time_data(macro_ticker, self.db, user_id=self.current_user.id)

            top_holdings = sorted(holdings, key=lambda item: item.market_value, reverse=True)[:3]
            top_tickers = [holding.ticker for holding in top_holdings]

            for ticker in top_tickers:
                await MarketDataService.get_real_time_data(ticker, self.db, user_id=self.current_user.id)

            relevant_tickers = [macro_ticker] + top_tickers
            all_news = await self.repo.get_stock_news(relevant_tickers, limit=15)

            if all_news:
                market_news_context = "\n".join(
                    [f"- [{news.ticker}] {news.title} ({news.publisher})" for news in all_news]
                )
                logger.info(f"Aggregated {len(all_news)} news items for portfolio RAG context.")
        except Exception as exc:
            logger.error(f"Failed to fetch RAG news context: {exc}")
            await self.db.rollback()
        return market_news_context

    async def _build_macro_context(self) -> str:
        macro_context = ""
        try:
            radar_topics = await MacroService.get_latest_radar(self.db)
            if radar_topics:
                macro_context += "### 宏观热点雷达 (Macro Radar):\n"
                for topic in radar_topics[:3]:
                    macro_context += f"- **{topic.title}** (热度: {topic.heat_score}): {topic.summary}\n"

            global_news = await MacroService.get_latest_news(self.db, limit=5)
            if global_news:
                macro_context += "\n### 实时全球快讯 (Real-time Global Flash):\n"
                for news in global_news:
                    macro_context += f"- [{news.published_at}] {news.content[:150]}...\n"

            if not macro_context:
                macro_context = "当前无显著宏观热点波动。"
        except Exception as exc:
            logger.error(f"Failed to fetch macro context for portfolio RAG: {exc}")
            await self.db.rollback()
            macro_context = "宏观数据检索失败。"
        return macro_context

    async def _persist_report(
        self,
        parsed_data: dict[str, Any],
        ai_raw_response: str,
        preferred_model: str,
    ) -> PortfolioAnalysisReport | None:
        try:
            new_portfolio_report = PortfolioAnalysisReport(
                user_id=self.current_user.id,
                health_score=float(parsed_data.get("health_score", 50)),
                risk_level=str(parsed_data.get("risk_level", "中")),
                summary=str(parsed_data.get("summary", "投资组合概览")),
                diversification_analysis=str(parsed_data.get("diversification_analysis", "分散度分析见详细报告")),
                strategic_advice=str(parsed_data.get("strategic_advice", "保持关注")),
                top_risks=parsed_data.get("top_risks", []),
                top_opportunities=parsed_data.get("top_opportunities", []),
                detailed_report=str(parsed_data.get("detailed_report", ai_raw_response)),
                model_used=preferred_model,
            )
            await self.repo.save_portfolio_analysis(new_portfolio_report)
            logger.info(f"Successfully persisted portfolio analysis report for user {self.current_user.id}")
            return new_portfolio_report
        except Exception as exc:
            logger.error(f"Failed to persist portfolio analysis: {exc}")
            await self.repo.rollback()
            return None


class GetLatestPortfolioAnalysisUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = PortfolioRepository(db)

    async def execute(self) -> PortfolioAnalysisResponse:
        report = await self.repo.latest_portfolio_analysis(self.current_user.id)

        if not report:
            raise HTTPException(status_code=404, detail="No portfolio analysis found. Please generate one first.")

        # Discard stale "failed" records so the frontend shows the generate button
        if report.risk_level == "未知" or report.summary in ("调用失败", "解析失败"):
            raise HTTPException(status_code=404, detail="No valid portfolio analysis found. Please generate one.")

        return PortfolioAnalysisResponse(
            health_score=int(report.health_score),
            risk_level=report.risk_level,
            summary=report.summary,
            diversification_analysis=report.diversification_analysis or "",
            strategic_advice=report.strategic_advice or "",
            top_risks=report.top_risks or [],
            top_opportunities=report.top_opportunities or [],
            detailed_report=report.detailed_report,
            model_used=report.model_used,
            created_at=report.created_at,
        )
