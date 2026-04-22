from __future__ import annotations
import logging
from typing import List, Dict, Any
from datetime import datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.macro_repository import MacroRepository
from app.models.macro import MacroTopic, GlobalNews, GlobalHourlyReport
from app.services.macro_ai_service import MacroAIService
from app.services.macro_fetcher import MacroFetcher
from app.services.macro_notifier import MacroNotifier
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)

class MacroService:
    """
    【宏观调度服务 (Macro Service)】
    作为宏观经济子系统的核心调度中心，负责协调数据抓取 (Fetcher)、AI 分析 (AIService) 和数据持久化 (Repository)。
    主要业务流包括：
    1. 全球宏观雷达：监控地缘政治、美联储政策等重大事件。
    2. 全球快讯：监控财联社等合规源的实时新闻。
    3. 整点精要：每小时自动汇总并利用 AI 生成深度市场综述及持仓穿透分析。
    """
    @staticmethod
    def _repo(db: AsyncSession) -> MacroRepository:
        """初始化宏观数据仓库"""
        return MacroRepository(db)

    @staticmethod
    def _prepare_radar_news(news_items: list[dict], max_items: int = 18) -> list[dict]:
        """压缩并去重新闻输入，降低 AI 提示长度和响应时间。"""
        deduped: list[dict] = []
        seen: set[str] = set()

        for item in news_items:
            title = str(item.get("title") or "").strip()
            content = str(item.get("content") or "").strip()
            if not title and not content:
                continue

            fingerprint = f"{title.lower()}|{content[:120].lower()}"
            if fingerprint in seen:
                continue

            seen.add(fingerprint)
            deduped.append(item)
            if len(deduped) >= max_items:
                break

        return deduped

    @staticmethod
    async def update_global_radar(db: AsyncSession = None, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """
        [业务入口] 抓取并持久化宏观雷达热点。
        支持后台异步调用（db 为空时自动创建会话）。该方法是雷达更新的总入口，协调会话生命周期。
        """
        if db is None:
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_global_radar_internal(new_db, api_key_siliconflow)
        return await MacroService._update_global_radar_internal(db, api_key_siliconflow)

    @staticmethod
    async def _update_global_radar_internal(db: AsyncSession, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """
        [核心逻辑] 宏观雷达更新流程：
        1. 外部数据抓取：调用 Tavily 搜索全球最新宏观动态。
        2. 容错回退机制：若外部抓取失败或超时，自动回退到本地数据库最近 24 小时的快讯库，确保系统在断网/API 受限时仍能通过本地数据产生分析。
        3. AI 模型深度提炼：利用大模型对碎片化新闻进行语义聚合，识别出核心议题，并执行多维打分（量化热度）。
        4. 持久化与分发：Upsert 模式更新主题库，并触发多渠道异步通知。
        """
        logger.info("Starting global macro radar update...")
        repo = MacroService._repo(db)
        started_at = perf_counter()
        try:
            # 1. 抓取全球实时宏观动态 (Tavily Provider)
            all_news_raw = await MacroFetcher.fetch_radar_news()
            fetch_elapsed = perf_counter() - started_at
            
            # 2. 容错兜底：若抓取失败，则利用本地已有的最新快讯进行分析
            if not all_news_raw:
                logger.warning("External fetch failed, falling back to local news cache...")
                all_news_raw = await repo.get_recent_news_for_radar()
            
            if not all_news_raw:
                logger.error("No external or local news available for macro radar update.")
                return []

            prepared_news = MacroService._prepare_radar_news(all_news_raw)

            logger.info(
                "Data source ready. Proceeding to AI analyzer with %s items (raw=%s, fetch=%.2fs)...",
                len(prepared_news),
                len(all_news_raw),
                fetch_elapsed,
            )
            
            # 3. AI 深度解析：产出结构化的宏观主题 (包含利好/利空板块指引)
            ai_started_at = perf_counter()
            topics_data = await MacroAIService.analyze_radar_topics(prepared_news, db, api_key_siliconflow)
            ai_elapsed = perf_counter() - ai_started_at
            
            if not topics_data:
                logger.warning("Macro radar AI returned no topics (fetch=%.2fs, ai=%.2fs)", fetch_elapsed, ai_elapsed)
                return []

            # 4. 数据落地 (Upsert 模式确保不重复添加相同主题，仅更新其热度与最新新闻引用)
            persist_started_at = perf_counter()
            new_topics = await repo.upsert_topics(topics_data)
            persist_elapsed = perf_counter() - persist_started_at
            
            # 5. 推送提醒：根据用户订阅状态分发飞书/终端通知 (异步非阻塞)
            users = await repo.get_macro_alert_users()
            total_elapsed = perf_counter() - started_at
            logger.info(
                "Successfully processed %s macro topics (fetch=%.2fs, ai=%.2fs, persist=%.2fs, total=%.2fs).",
                len(new_topics),
                fetch_elapsed,
                ai_elapsed,
                persist_elapsed,
                total_elapsed,
            )
            await MacroNotifier.notify_topics(users, new_topics)
            
            return new_topics

        except Exception as e:
            logger.error(f"Macro AI processing failed: {e}")
            await repo.rollback()
            return []

    @staticmethod
    async def get_latest_radar(db: AsyncSession) -> List[MacroTopic]:
        """
        [数据查询] 获取最新的宏观雷达主题列表。
        该列表通常用于前端“发现”页面的瀑布流展示，按热度和时间权重排序。
        """
        return await MacroService._repo(db).get_latest_topics()

    @staticmethod
    async def update_cls_news(db: AsyncSession = None) -> List[GlobalNews]:
        """
        [业务入口] 抓取并持久化财联社 (CLS) 全球快讯。
        快讯流提供了比雷达热点更细粒度、更及时的碎片化信息。
        """
        if db is None:
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_cls_news_internal(new_db)
        return await MacroService._update_cls_news_internal(db)

    @staticmethod
    async def _update_cls_news_internal(db: AsyncSession) -> List[GlobalNews]:
        """
        [逻辑实现] 调用 AKShare 获取财联社全球快讯流，并进行指纹去重持久化。
        """
        logger.info("Starting Cailianshe global news update (Standard Version)...")
        repo = MacroService._repo(db)
        try:
            # 抓取原始 DataFrame 并构建模型列表
            news_df = await MacroFetcher.fetch_cls_news_rows()
            return await repo.persist_cls_news(MacroFetcher.build_news_items_from_df(news_df))
        except Exception as e:
            logger.error(f"Failed to update news: {e}")
            await repo.rollback()
            return []

    @staticmethod
    async def update_cls_headlines(db: AsyncSession = None) -> List[GlobalNews]:
        """
        [业务入口] 更新全球快讯头条（update_cls_news 的别名）。
        """
        return await MacroService.update_cls_news(db)

    @staticmethod
    async def generate_global_hourly_report(db: AsyncSession) -> GlobalHourlyReport | None:
        """
        [整点精要] 定时汇总过去 1 小时快讯，生成全局宏观综述：
        1. 窗口期数据提取：仅抓取上一整点至今的所有快讯。
        2. 幂等性控制：通过 YYYY-MM-DD-HH 作为 Key 预检，防止多节点部署导致的重复生成。
        3. 核心穿透分析：生成 'impact_map' (标的 -> 影响逻辑)，这是后续实现“持仓透视”功能的关键数据结构。
        """
        repo = MacroService._repo(db)
        news_items = await repo.get_recent_news_for_hourly_report()
        if not news_items:
            return None

        now = utc_now_naive()
        hour_key = now.strftime("%Y-%m-%d-%H")

        # 缓存检查：同一小时不再重复生成
        existing_report = await repo.get_hourly_report(hour_key)
        if existing_report:
            logger.info(f"Global hourly report for {hour_key} already exists. Skipping AI call.")
            return existing_report

        try:
            # 调用 AI 生成高度压缩的精要总结
            # 此处会产出核心摘要、情绪倾向以及 影响标的 -> 逻辑 的映射表
            parsed_report = await MacroAIService.generate_hourly_report(news_items, db)
            
            # 保存报告并关联到对应小时的 Key
            new_report, existed = await repo.get_or_create_hourly_report(hour_key, parsed_report, len(news_items))
            if existed:
                logger.info(f"Global hourly report for {hour_key} already exists. Skipping AI call.")
            elif new_report:
                logger.info(f"Successfully generated global hourly report for {hour_key}")
            return new_report
        except Exception as e:
            logger.error(f"Failed to generate global hourly report: {e}")
            await repo.rollback()
            return None

    @staticmethod
    async def generate_hourly_news_summary(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        [个性化透视] 将全局整点报告与用户持仓进行匹配：
        1. 获取关联报告：若当前整点报告尚未生成，内部会自动触发 generate_global_hourly_report。
        2. 持仓比对逻辑：从用户的 Portfolio 中提取所有 Ticker，与报告中的 'impact_map' 做交集。
        3. 智能呈现：若无直接影响，则提示“持仓未受影响”，减少用户焦虑及无用信息骚扰。
        """
        # 1. 获取全局报告基准 (若缺失则即时触发 AI 解析)
        global_report = await MacroService.generate_global_hourly_report(db)
        if not global_report:
            return {"summary": "本小时暂无关键新闻或 AI 分析正在生成中。", "count": 0}

        # 2. 获取用户持仓数据 (仅限 Ticker 列表，用于高效碰撞)
        user_tickers = await MacroService._repo(db).get_user_portfolio_tickers(user_id)

        # 3. 执行个性化过滤：筛选出影响到用户持仓的条目
        personalized_impact = []
        impact_map = global_report.impact_map or {}
        
        for ticker, reason in impact_map.items():
            if ticker in user_tickers:
                # 提取 AI 对该特定标的的诊断逻辑
                personalized_impact.append(f"**{ticker}**: {reason}")

        # 4. 拼装多级总结内容 (基础概况 + 深度持仓扫描)
        summary = global_report.core_summary
        if personalized_impact:
            summary += "\n\n**【持仓穿透】**\n" + "\n".join(personalized_impact)
        else:
            summary += "\n\n**【持仓穿透】**\n当前持仓未受本小时核心事件显著影响。"

        return {
            "summary": summary,
            "count": int(global_report.news_count),
            "sentiment": global_report.sentiment
        }

    @staticmethod
    async def get_latest_news(db: AsyncSession, limit: int = 50) -> List[GlobalNews]:
        """
        [数据查询] 获取最新的快讯时间线。
        默认返回最近 50 条，用于前端“宏观时间轴”组件的实时渲染。
        """
        return await MacroService._repo(db).get_latest_news(limit=limit)
    @staticmethod
    async def get_radar_portfolio_alerts(user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        [雷达持仓穿透] 将最新宏观雷达主题与用户持仓做 Ticker 级别交叉比对。

        输出结构：
        - alerts: 命中的具体告警项（含方向/主题/时间层/传导逻辑）
        - market_pulse: 当前市场体温（从最新 topic 中提取）
        - total_topics: 本次扫描的主题数
        - affected_tickers: 持仓中被命中的 Ticker 集合
        """
        repo = MacroService._repo(db)

        # 1. 并发获取主题列表 + 用户持仓
        topics = await repo.get_latest_topics(limit=10)
        user_tickers = set(await repo.get_user_portfolio_tickers(user_id))

        if not topics or not user_tickers:
            return {
                "alerts": [],
                "market_pulse": {},
                "total_topics": len(topics),
                "affected_tickers": [],
            }

        # 2. 提取最新的 market_pulse（取热度最高主题的 pulse）
        market_pulse = {}
        for t in sorted(topics, key=lambda x: x.heat_score or 0, reverse=True):
            ia = t.impact_analysis or {}
            if ia.get("market_pulse"):
                market_pulse = ia["market_pulse"]
                break

        # 3. 逐主题扫描 beneficiaries / detriments，与持仓做碰撞
        alerts: list[Dict[str, Any]] = []
        seen: set[str] = set()  # 去重 (ticker, topic_id)

        for topic in topics:
            ia = topic.impact_analysis or {}
            time_layer = ia.get("time_layer", "narrative")
            logic = ia.get("logic", "")

            for entry in ia.get("beneficiaries", []):
                ticker = (entry.get("ticker") or "").upper().strip()
                if ticker and ticker in user_tickers:
                    key = f"{ticker}:{topic.id}:bull"
                    if key not in seen:
                        seen.add(key)
                        alerts.append({
                            "ticker": ticker,
                            "direction": "bullish",
                            "topic_title": topic.title,
                            "topic_heat": topic.heat_score,
                            "time_layer": time_layer,
                            "reason": entry.get("reason", ""),
                            "logic": logic,
                        })

            for entry in ia.get("detriments", []):
                ticker = (entry.get("ticker") or "").upper().strip()
                if ticker and ticker in user_tickers:
                    key = f"{ticker}:{topic.id}:bear"
                    if key not in seen:
                        seen.add(key)
                        alerts.append({
                            "ticker": ticker,
                            "direction": "bearish",
                            "topic_title": topic.title,
                            "topic_heat": topic.heat_score,
                            "time_layer": time_layer,
                            "reason": entry.get("reason", ""),
                            "logic": logic,
                        })

        # 4. 按热度降序排列，让最重要的告警最先显示
        alerts.sort(key=lambda a: a["topic_heat"] or 0, reverse=True)

        affected_tickers = list({a["ticker"] for a in alerts})

        logger.info(
            f"[RadarPenetration] user={user_id} | "
            f"portfolio={len(user_tickers)} tickers | "
            f"topics={len(topics)} | alerts={len(alerts)}"
        )

        return {
            "alerts": alerts,
            "market_pulse": market_pulse,
            "total_topics": len(topics),
            "affected_tickers": affected_tickers,
        }