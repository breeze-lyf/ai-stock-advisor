import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analysis.mappers import serialize_analysis_report
from app.application.analysis.helpers import (
    extract_entry_prices_fallback,
    extract_entry_zone_fallback,
    to_float,
    to_str,
)
from app.core.security import sanitize_float
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.models.analysis import AnalysisReport
from app.models.stock import Stock
from app.models.user import User
from app.services.ai_service import AIService
from app.services.macro_service import MacroService
from app.services.market_data import MarketDataService
from app.utils.ai_response_parser import parse_ai_json

logger = logging.getLogger(__name__)


class AnalyzeStockUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def execute(self, ticker: str, force: bool = False) -> dict[str, Any]:
        ticker = ticker.upper().strip()

        await self._check_free_tier_limit()

        stock_obj = await self._get_stock(ticker)
        market_data_obj = await MarketDataService.get_real_time_data(ticker, self.db, force_refresh=force)
        market_data = self._build_market_data(market_data_obj)
        news_data = await self._get_news_data(ticker)
        portfolio_data = await self._get_portfolio_data(ticker, market_data)
        macro_context = await self._get_macro_context()
        fundamental_data = self._build_fundamental_data(stock_obj, market_data_obj)

        logger.info(f"Preparing AI analysis for {ticker}. Market Data keys present: {list(market_data.keys())}")
        if not market_data.get("rsi_14"):
            logger.warning(f"Technical indicators missing for {ticker}, prompt may be low quality.")

        preferred_model = self.current_user.preferred_ai_model or "gemini-1.5-flash"

        cached_response = await self._get_cached_response(ticker, market_data, preferred_model, force)
        if cached_response:
            return cached_response

        previous_analysis_context = await self._build_previous_analysis_context(ticker)

        ai_raw_response = await AIService.generate_analysis(
            ticker,
            market_data,
            portfolio_data,
            news_data,
            macro_context=macro_context,
            fundamental_data=fundamental_data,
            previous_analysis=previous_analysis_context,
            model=preferred_model,
            db=self.db,
            user_id=self.current_user.id,
        )
        logger.info(f"AI Response for {ticker}: {ai_raw_response}")

        parsed_data = parse_ai_json(ai_raw_response, context=f"stock_{ticker}")
        final_rr_str = self._resolve_rr_ratio(parsed_data, market_data)
        new_report = await self._persist_report(
            ticker=ticker,
            preferred_model=preferred_model,
            ai_raw_response=ai_raw_response,
            parsed_data=parsed_data,
            market_data=market_data,
            portfolio_data=portfolio_data,
            final_rr_str=final_rr_str,
        )
        await self._sync_ai_rrr_to_cache(ticker, market_data, new_report)

        return {
            "ticker": ticker,
            "sentiment_score": to_float(parsed_data.get("sentiment_score")),
            "summary_status": to_str(parsed_data.get("summary_status")),
            "risk_level": to_str(parsed_data.get("risk_level")),
            "technical_analysis": to_str(parsed_data.get("technical_analysis")),
            "fundamental_news": to_str(parsed_data.get("fundamental_news")),
            "news_summary": to_str(parsed_data.get("news_summary")) or to_str(parsed_data.get("fundamental_news")),
            "fundamental_analysis": to_str(parsed_data.get("fundamental_analysis")),
            "macro_risk_note": to_str(parsed_data.get("macro_risk_note")),
            "action_advice": to_str(parsed_data.get("action_advice")),
            "investment_horizon": to_str(parsed_data.get("investment_horizon")),
            "confidence_level": to_float(parsed_data.get("confidence_level")),
            "immediate_action": to_str(parsed_data.get("immediate_action")),
            "target_price": to_float(parsed_data.get("target_price")),
            "stop_loss_price": to_float(parsed_data.get("stop_loss_price")),
            "entry_zone": new_report.entry_zone if new_report else to_str(parsed_data.get("entry_zone")),
            "entry_price_low": new_report.entry_price_low if new_report else to_float(parsed_data.get("entry_price_low")),
            "entry_price_high": new_report.entry_price_high if new_report else to_float(parsed_data.get("entry_price_high")),
            "rr_ratio": final_rr_str,
            "scenario_tags": parsed_data.get("scenario_tags"),
            "thought_process": parsed_data.get("thought_process"),
            "is_cached": False,
            "model_used": preferred_model,
            "created_at": new_report.created_at if new_report else datetime.utcnow(),
        }

    async def _check_free_tier_limit(self):
        if self.current_user.api_key_gemini:
            return

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self.repo.count_reports_since(self.current_user.id, today_start)
        if count >= 3:
            raise HTTPException(
                status_code=429,
                detail="Free tier limit reached (3/day). Please add your own API Key in Settings for unlimited access.",
            )

    async def _get_stock(self, ticker: str) -> Optional[Stock]:
        return await self.repo.get_stock(ticker)

    def _build_market_data(self, market_data_obj: Any) -> dict[str, Any]:
        if hasattr(market_data_obj, "__dict__"):
            return {
                "current_price": sanitize_float(market_data_obj.current_price, 0.0),
                "change_percent": sanitize_float(market_data_obj.change_percent, 0.0),
                "rsi_14": sanitize_float(market_data_obj.rsi_14),
                "ma_20": sanitize_float(market_data_obj.ma_20),
                "ma_50": sanitize_float(market_data_obj.ma_50),
                "ma_200": sanitize_float(market_data_obj.ma_200),
                "macd_val": sanitize_float(market_data_obj.macd_val),
                "macd_hist": sanitize_float(market_data_obj.macd_hist),
                "macd_hist_slope": sanitize_float(market_data_obj.macd_hist_slope, 0.0),
                "bb_upper": sanitize_float(market_data_obj.bb_upper),
                "bb_middle": sanitize_float(market_data_obj.bb_middle),
                "bb_lower": sanitize_float(market_data_obj.bb_lower),
                "k_line": sanitize_float(market_data_obj.k_line),
                "d_line": sanitize_float(market_data_obj.d_line),
                "j_line": sanitize_float(market_data_obj.j_line),
                "atr_14": sanitize_float(market_data_obj.atr_14),
                "adx_14": sanitize_float(market_data_obj.adx_14),
                "resistance_1": sanitize_float(market_data_obj.resistance_1),
                "resistance_2": sanitize_float(market_data_obj.resistance_2),
                "support_1": sanitize_float(market_data_obj.support_1),
                "support_2": sanitize_float(market_data_obj.support_2),
                "market_status": market_data_obj.market_status,
            }

        return {
            "current_price": market_data_obj.get("currentPrice"),
            "change_percent": market_data_obj.get("regularMarketChangePercent"),
            "rsi_14": 50.0,
            "market_status": "OPEN",
        }

    async def _get_news_data(self, ticker: str) -> list[dict[str, Any]]:
        news_articles = await self.repo.get_latest_stock_news(ticker, limit=5)
        return [
            {"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()}
            for n in news_articles
        ]

    async def _get_portfolio_data(self, ticker: str, market_data: dict[str, Any]) -> dict[str, Any]:
        portfolio_item = await self.repo.get_portfolio_item(self.current_user.id, ticker)
        if not portfolio_item:
            return {}

        current_price = market_data["current_price"] or 0
        unrealized_pl = (current_price - portfolio_item.avg_cost) * portfolio_item.quantity
        pl_percent = (
            (unrealized_pl / (portfolio_item.avg_cost * portfolio_item.quantity) * 100)
            if (portfolio_item.avg_cost > 0 and portfolio_item.quantity > 0)
            else 0
        )
        return {
            "avg_cost": portfolio_item.avg_cost,
            "quantity": portfolio_item.quantity,
            "unrealized_pl": unrealized_pl,
            "pl_percent": pl_percent,
        }

    async def _get_macro_context(self) -> str:
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
            logger.error(f"Failed to fetch macro context for RAG: {exc}")
            macro_context = "宏观数据检索失败。"
        return macro_context

    def _build_fundamental_data(self, stock_obj: Optional[Stock], market_data_obj: Any) -> dict[str, Any]:
        if not stock_obj:
            return {}
        return {
            "sector": stock_obj.sector,
            "industry": stock_obj.industry,
            "market_cap": sanitize_float(stock_obj.market_cap),
            "pe_ratio": sanitize_float(stock_obj.pe_ratio),
            "forward_pe": sanitize_float(stock_obj.forward_pe),
            "eps": sanitize_float(stock_obj.eps),
            "dividend_yield": sanitize_float(stock_obj.dividend_yield),
            "beta": sanitize_float(stock_obj.beta),
            "fifty_two_week_high": sanitize_float(stock_obj.fifty_two_week_high),
            "fifty_two_week_low": sanitize_float(stock_obj.fifty_two_week_low),
            "pe_percentile": sanitize_float(market_data_obj.pe_percentile) if market_data_obj else None,
            "pb_percentile": sanitize_float(market_data_obj.pb_percentile) if market_data_obj else None,
            "net_inflow": sanitize_float(market_data_obj.net_inflow) if market_data_obj else None,
        }

    async def _get_cached_response(
        self,
        ticker: str,
        market_data: dict[str, Any],
        preferred_model: str,
        force: bool,
    ) -> Optional[dict[str, Any]]:
        if force:
            return None

        cached_report = await self.repo.get_latest_report(self.current_user.id, ticker)

        if not cached_report or not cached_report.technical_analysis:
            return None

        if cached_report.entry_price_low is None and cached_report.entry_price_high is None:
            cached_report.entry_price_low, cached_report.entry_price_high = extract_entry_prices_fallback(
                cached_report.action_advice
            )

        final_rr = cached_report.rr_ratio
        if not final_rr and cached_report.target_price and cached_report.stop_loss_price:
            curr_p = market_data.get("current_price") or 0.0
            reward = cached_report.target_price - curr_p
            risk = curr_p - cached_report.stop_loss_price
            if risk > 0 and reward > 0:
                final_rr = f"{reward/risk:.2f}"

        logger.info(f"Returning latest report for {ticker} (model: {preferred_model})")
        return serialize_analysis_report(cached_report, rr_ratio=final_rr)

    async def _build_previous_analysis_context(self, ticker: str) -> Optional[dict[str, Any]]:
        last_report = await self.repo.get_latest_report(self.current_user.id, ticker)
        if not last_report:
            return None

        diff = datetime.utcnow() - last_report.created_at
        if diff.days > 0:
            time_ago = f"{diff.days}天前"
        elif diff.seconds > 3600:
            time_ago = f"{diff.seconds // 3600}小时前"
        else:
            time_ago = f"{diff.seconds // 60}分钟前"

        logger.info(f"Loaded historical analysis context for {ticker} from {time_ago}")
        return {
            "time": f"{last_report.created_at.strftime('%Y-%m-%d %H:%M')} ({time_ago})",
            "summary_status": last_report.summary_status,
            "sentiment_score": last_report.sentiment_score,
            "immediate_action": last_report.immediate_action,
            "target_price": last_report.target_price,
            "stop_loss_price": last_report.stop_loss_price,
            "entry_price_low": last_report.entry_price_low,
            "entry_price_high": last_report.entry_price_high,
            "risk_level": last_report.risk_level,
            "investment_horizon": last_report.investment_horizon,
            "confidence_level": last_report.confidence_level,
            "action_advice_short": last_report.action_advice[:200] if last_report.action_advice else "",
        }

    def _resolve_rr_ratio(self, parsed_data: dict[str, Any], market_data: dict[str, Any]) -> Optional[str]:
        final_rr_str = to_str(parsed_data.get("rr_ratio"))
        if final_rr_str:
            import re

            colon_match = re.search(r"[:：]\s*(\d+(?:\.\d+)?)", final_rr_str)
            if colon_match:
                return f"{float(colon_match.group(1)):.2f}"

            number_match = re.search(r"(\d+(?:\.\d+)?)", final_rr_str)
            if number_match:
                return f"{float(number_match.group(1)):.2f}"

        target = to_float(parsed_data.get("target_price"))
        stop = to_float(parsed_data.get("stop_loss_price"))
        curr_p = market_data.get("current_price") or 0.0
        if target and stop and curr_p:
            reward = target - curr_p
            risk = curr_p - stop
            if risk > 0 and reward > 0:
                return f"{reward/risk:.2f}"
        return final_rr_str

    async def _persist_report(
        self,
        ticker: str,
        preferred_model: str,
        ai_raw_response: str,
        parsed_data: dict[str, Any],
        market_data: dict[str, Any],
        portfolio_data: dict[str, Any],
        final_rr_str: Optional[str],
    ) -> Optional[AnalysisReport]:
        new_report = None
        try:
            new_report = AnalysisReport(
                user_id=self.current_user.id,
                ticker=ticker,
                model_used=preferred_model,
                ai_response_markdown=ai_raw_response,
                sentiment_score=to_str(parsed_data.get("sentiment_score")),
                summary_status=to_str(parsed_data.get("summary_status")),
                risk_level=to_str(parsed_data.get("risk_level")),
                technical_analysis=to_str(parsed_data.get("technical_analysis")),
                fundamental_news=to_str(parsed_data.get("news_summary")) or to_str(parsed_data.get("fundamental_news")),
                confidence_level=to_float(parsed_data.get("confidence_level")),
                immediate_action=to_str(parsed_data.get("immediate_action")),
                action_advice=to_str(parsed_data.get("action_advice")),
                investment_horizon=to_str(parsed_data.get("investment_horizon")),
                target_price=to_float(parsed_data.get("target_price")),
                stop_loss_price=to_float(parsed_data.get("stop_loss_price")),
                entry_zone=to_str(parsed_data.get("entry_zone")),
                entry_price_low=to_float(parsed_data.get("entry_price_low")),
                entry_price_high=to_float(parsed_data.get("entry_price_high")),
                rr_ratio=final_rr_str,
                scenario_tags=parsed_data.get("scenario_tags"),
                thought_process=parsed_data.get("thought_process"),
                input_context_snapshot={
                    "market_data": market_data,
                    "portfolio_data": portfolio_data,
                },
            )
            if new_report.entry_price_low is None and new_report.entry_price_high is None:
                new_report.entry_price_low, new_report.entry_price_high = extract_entry_prices_fallback(
                    new_report.action_advice
                )
            if not new_report.entry_zone:
                new_report.entry_zone = extract_entry_zone_fallback(new_report.action_advice)

            new_report = await self.repo.add_report(new_report)
        except Exception as exc:
            logger.error(f"Failed to persist structured analysis report: {exc}")
            await self.repo.rollback()
        return new_report

    async def _sync_ai_rrr_to_cache(
        self,
        ticker: str,
        market_data: dict[str, Any],
        new_report: Optional[AnalysisReport],
    ):
        try:
            if not new_report:
                return

            cache_to_sync = await self.repo.get_market_cache(ticker)
            if not cache_to_sync:
                return

            effective_rrr = None
            try:
                if new_report.rr_ratio:
                    effective_rrr = float(new_report.rr_ratio)
            except (ValueError, TypeError):
                effective_rrr = None

            if effective_rrr is None and new_report.target_price and new_report.stop_loss_price:
                curr_p = market_data.get("current_price") or 0.0
                reward = new_report.target_price - curr_p
                risk = curr_p - new_report.stop_loss_price
                if risk > 0 and reward > 0:
                    effective_rrr = round(reward / risk, 2)

            if effective_rrr is None:
                return

            cache_to_sync.risk_reward_ratio = effective_rrr
            cache_to_sync.is_ai_strategy = True
            cache_to_sync.resistance_1 = new_report.target_price
            cache_to_sync.support_1 = new_report.stop_loss_price
            await self.repo.save_market_cache(cache_to_sync)
            logger.info(f"✅ Synced AI RRR ({effective_rrr}) to MarketDataCache for {ticker} (Strategy Locked)")
        except Exception as exc:
            logger.error(f"Failed to sync AI RRR to cache: {exc}")
            await self.repo.rollback()
