import logging
import asyncio
import time
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
from app.core.config import settings
from app.core.security import sanitize_float
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.infrastructure.db.repositories.user_provider_credential_repository import UserProviderCredentialRepository
from app.models.analysis import AnalysisReport
from app.models.stock import Stock
from app.models.user import MembershipTier, User
from app.services.ai_service import AIService
from app.services.macro_service import MacroService
from app.services.market_data import MarketDataService
from app.utils.ai_response_parser import parse_ai_json

logger = logging.getLogger(__name__)


def _log_duration(label: str, start: float) -> float:
    """打印耗时并返回当前时间戳"""
    elapsed = time.time() - start
    logger.info(f"⏱️ [{label}] 耗时: {elapsed:.2f}秒")
    return time.time()


class AnalyzeStockUseCase:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        self.repo = AnalysisRepository(db)

    async def _has_personal_api_key(self) -> bool:
        # Legacy user-level keys
        if bool(self.current_user.api_key_deepseek) or bool(self.current_user.api_key_siliconflow):
            return True

        # Unified provider credentials
        try:
            credential_repo = UserProviderCredentialRepository(self.db)
            credentials = await credential_repo.list_by_user_id(self.current_user.id)
            return any(bool(item.encrypted_api_key) and bool(item.is_enabled) for item in credentials)
        except Exception as exc:
            logger.warning(f"Failed to inspect provider credentials for user {self.current_user.id}: {exc}")
            return False

    async def execute(self, ticker: str, force: bool = False) -> dict[str, Any]:
        total_start = time.time()
        ticker = ticker.upper().strip()
        logger.info(f"🚀 开始分析股票: {ticker}")

        preferred_model = self.current_user.preferred_ai_model or settings.DEFAULT_AI_MODEL
        step_start = _log_duration("Step 1: 初始化分析参数", total_start)

        # Step 2: Parallel data fetching for all components
        logger.info(f"Starting parallel data fetching for {ticker}...")
        fetch_start = time.time()
        results = await asyncio.gather(
            self._get_stock(ticker),
            MarketDataService.get_real_time_data(
                ticker,
                self.db,
                force_refresh=force,
                user_id=self.current_user.id,
            ),
            self._get_news_data(ticker),
            self._get_macro_context(),
            return_exceptions=True
        )
        fetch_elapsed = time.time() - fetch_start
        logger.info(f"⏱️ [Step 2: 并行数据获取] 总耗时: {fetch_elapsed:.2f}秒")
        
        # Unpack results with error handling
        stock_obj = results[0] if not isinstance(results[0], Exception) else None
        market_data_obj = results[1] if not isinstance(results[1], Exception) else None
        news_data = results[2] if not isinstance(results[2], Exception) else []
        macro_context = results[3] if not isinstance(results[3], Exception) else ""
        
        # 打印各子任务的耗时
        logger.info(f"   - 股票基础信息: {'✅ 成功' if stock_obj else '❌ 失败'}")
        logger.info(f"   - 实时行情数据: {'✅ 成功' if market_data_obj else '❌ 失败'}")
        logger.info(f"   - 新闻数据: {'✅ 成功' if news_data else '❌ 失败'} ({len(news_data)}条)")
        logger.info(f"   - 宏观上下文: {'✅ 成功' if macro_context else '❌ 失败'} ({len(macro_context) if macro_context else 0}字符)")
        
        if isinstance(results[1], Exception):
            logger.error(f"Failed to fetch market data for {ticker}: {results[1]}")
            raise HTTPException(status_code=500, detail=f"Market data fetch error: {str(results[1])}")
        
        # Step 3: Build derived data objects
        build_start = time.time()
        market_data = self._build_market_data(market_data_obj)
        fundamental_data = self._build_fundamental_data(stock_obj, market_data_obj)
        _log_duration("Step 3: 数据构建", build_start)
        
        logger.info(f"Preparing AI analysis for {ticker}. Market Data keys present: {list(market_data.keys())}")
        if not market_data.get("rsi_14"):
            logger.warning(f"Technical indicators missing for {ticker}, prompt may be low quality.")

        logger.info(f"📌 使用 AI 模型: {preferred_model}")

        # 检查缓存
        cache_start = time.time()
        cached_response = await self._get_cached_response(ticker, market_data, preferred_model, force)
        if cached_response:
            _log_duration("Step 5: 缓存命中（跳过AI调用）", cache_start)
            total_elapsed = time.time() - total_start
            logger.info(f"🎉 总耗时: {total_elapsed:.2f}秒 (从缓存返回)")
            cached_response["total_duration"] = total_elapsed
            return cached_response
        _log_duration("Step 5: 缓存检查", cache_start)

        await self._check_free_tier_limit()
        _log_duration("Step 5.1: 免费用户检查", cache_start)

        previous_analysis_context = await self._build_previous_analysis_context(ticker)

        # 🚀 重要: 在进入耗时 2分钟+ 的 AI 生成阶段前，提交当前事务。
        # 这样可以确保在该线程/协程等待 AI 响应期间，数据库连接已经释放回连接池，供其他请求使用。
        # 防止在高并发或低配置环境下连接池枯竭。
        try:
            await self.db.commit()
        except Exception as e:
            logger.warning(f"数据库提交失败: {e}，继续执行")
            try:
                await self.db.rollback()
            except Exception:
                pass

        # 🚨 AI 分析阶段 - 这是最耗时的部分
        ai_start = time.time()
        logger.info(f"🤖 开始调用 AI (预计 60-180 秒)...")
        
        try:
            ai_raw_response = await AIService.generate_analysis(
                ticker,
                market_data,
                news_data,
                macro_context=macro_context,
                fundamental_data=fundamental_data,
                previous_analysis=previous_analysis_context,
                model=preferred_model,
                db=self.db,
                user_id=self.current_user.id,
            )
        except Exception as ai_error:
            logger.error(f"AI 分析调用失败: {ai_error}")
            # 尝试回滚事务
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=503, 
                detail=f"AI 服务暂时不可用: {str(ai_error)[:200]}"
            )
        
        ai_elapsed = time.time() - ai_start
        logger.info(f"⏱️ [Step 6: AI 分析调用] 耗时: {ai_elapsed:.2f}秒 ({ai_elapsed/60:.1f}分钟)")
        logger.info(f"AI Response length: {len(ai_raw_response)} 字符")

        # 解析 AI 响应
        parse_start = time.time()
        parsed_data = parse_ai_json(ai_raw_response, context=f"stock_{ticker}")
        _log_duration("Step 7: AI 响应解析", parse_start)

        final_rr_str = self._resolve_rr_ratio(parsed_data, market_data)
        
        # 持久化报告
        persist_start = time.time()
        new_report = await self._persist_report(
            ticker=ticker,
            preferred_model=preferred_model,
            ai_raw_response=ai_raw_response,
            parsed_data=parsed_data,
            market_data=market_data,
            final_rr_str=final_rr_str,
        )
        await self._sync_ai_rrr_to_cache(ticker, market_data, new_report)
        _log_duration("Step 8: 报告持久化", persist_start)

        total_elapsed = time.time() - total_start
        logger.info(f"🎉🎉🎉 分析完成! 总耗时: {total_elapsed:.2f}秒 ({total_elapsed/60:.1f}分钟)")

        return {
            "ticker": ticker,
            "decision_mode": to_str(parsed_data.get("decision_mode")),
            "dominant_driver": to_str(parsed_data.get("dominant_driver")),
            "trade_setup_status": to_str(parsed_data.get("trade_setup_status")),
            "sentiment_score": to_float(parsed_data.get("sentiment_score")),
            "summary_status": to_str(parsed_data.get("summary_status")),
            "risk_level": to_str(parsed_data.get("risk_level")),
            "trigger_condition": to_str(parsed_data.get("trigger_condition")),
            "invalidation_condition": to_str(parsed_data.get("invalidation_condition")),
            "next_review_point": to_str(parsed_data.get("next_review_point")),
            "technical_analysis": to_str(parsed_data.get("technical_analysis")),
            "fundamental_news": to_str(parsed_data.get("fundamental_news")),
            "news_summary": to_str(parsed_data.get("news_summary")) or to_str(parsed_data.get("fundamental_news")),
            "fundamental_analysis": to_str(parsed_data.get("fundamental_analysis")),
            "macro_risk_note": to_str(parsed_data.get("macro_risk_note")),
            "add_on_trigger": to_str(parsed_data.get("add_on_trigger")),
            "action_advice": to_str(parsed_data.get("action_advice")),
            "investment_horizon": to_str(parsed_data.get("investment_horizon")),
            "confidence_level": to_float(parsed_data.get("confidence_level")),
            "immediate_action": to_str(parsed_data.get("immediate_action")),
            "target_price": to_float(parsed_data.get("target_price")),
            "target_price_1": to_float(parsed_data.get("target_price_1")),
            "target_price_2": to_float(parsed_data.get("target_price_2")),
            "stop_loss_price": to_float(parsed_data.get("stop_loss_price")),
            "max_position_pct": to_float(parsed_data.get("max_position_pct")),
            "entry_zone": new_report.entry_zone if new_report else to_str(parsed_data.get("entry_zone")),
            "entry_price_low": new_report.entry_price_low if new_report else to_float(parsed_data.get("entry_price_low")),
            "entry_price_high": new_report.entry_price_high if new_report else to_float(parsed_data.get("entry_price_high")),
            "rr_ratio": final_rr_str,
            "bull_case": to_str(parsed_data.get("bull_case")),
            "base_case": to_str(parsed_data.get("base_case")),
            "bear_case": to_str(parsed_data.get("bear_case")),
            "scenario_tags": parsed_data.get("scenario_tags"),
            "thought_process": parsed_data.get("thought_process"),
            "is_cached": False,
            "model_used": preferred_model,
            "created_at": new_report.created_at if new_report else datetime.utcnow(),
        }

    async def _check_free_tier_limit(self):
        # 系统级 API Key (如 SiliconFlow) 的免费额度限制
        # 已配置个人 API Key 或非 FREE 用户，不受此限制。
        if (self.current_user.membership_tier or "").upper() != MembershipTier.FREE.value:
            return
        if await self._has_personal_api_key():
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

        cached_report = await self._get_latest_shared_report(ticker, preferred_model)

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
        last_report = await self._get_latest_shared_report(ticker, self.current_user.preferred_ai_model)
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

    async def _get_latest_shared_report(self, ticker: str, preferred_model: str | None) -> Optional[AnalysisReport]:
        candidates = await self.repo.get_latest_reports_for_ticker(ticker, limit=10, model_used=preferred_model)
        shared_report = self._pick_shared_scope_report(candidates)
        if shared_report:
            return shared_report

        if preferred_model:
            fallback_candidates = await self.repo.get_latest_reports_for_ticker(ticker, limit=10)
            return self._pick_shared_scope_report(fallback_candidates)

        return None

    @staticmethod
    def _pick_shared_scope_report(reports: list[AnalysisReport]) -> Optional[AnalysisReport]:
        if not reports:
            return None

        for report in reports:
            if getattr(report, "report_scope", None) == AnalysisRepository.SHARED_SCOPE:
                return report
            snapshot = report.input_context_snapshot or {}
            if isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared":
                return report
        return None

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
        final_rr_str: Optional[str],
    ) -> Optional[AnalysisReport]:
        new_report = None
        try:
            new_report = AnalysisReport(
                user_id=None,
                ticker=ticker,
                report_scope=AnalysisRepository.SHARED_SCOPE,
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
                    "analysis_scope": "stock_shared",
                },
            )
            if new_report.entry_price_low is None and new_report.entry_price_high is None:
                new_report.entry_price_low, new_report.entry_price_high = extract_entry_prices_fallback(
                    new_report.action_advice
                )
            if not new_report.entry_zone:
                new_report.entry_zone = extract_entry_zone_fallback(new_report.action_advice)

            new_report = await self.repo.add_report(new_report)
            await self._persist_user_interaction_record(ticker, preferred_model, new_report)
        except Exception as exc:
            logger.error(f"Failed to persist structured analysis report: {exc}")
            await self.repo.rollback()
        return new_report

    async def _persist_user_interaction_record(
        self,
        ticker: str,
        preferred_model: str,
        shared_report: AnalysisReport,
    ) -> None:
        interaction_record = AnalysisReport(
            user_id=self.current_user.id,
            ticker=ticker,
            report_scope=AnalysisRepository.USER_INTERACTION_SCOPE,
            model_used=preferred_model,
            summary_status=shared_report.summary_status,
            risk_level=shared_report.risk_level,
            confidence_level=shared_report.confidence_level,
            immediate_action=shared_report.immediate_action,
            investment_horizon=shared_report.investment_horizon,
            target_price=shared_report.target_price,
            stop_loss_price=shared_report.stop_loss_price,
            entry_zone=shared_report.entry_zone,
            entry_price_low=shared_report.entry_price_low,
            entry_price_high=shared_report.entry_price_high,
            rr_ratio=shared_report.rr_ratio,
            input_context_snapshot={
                "analysis_scope": "user_interaction",
                "interaction_type": "stock_analysis_request",
                "shared_report_id": shared_report.id,
            },
        )
        await self.repo.add_report(interaction_record)

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
