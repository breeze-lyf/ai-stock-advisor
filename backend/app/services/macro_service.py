from __future__ import annotations
import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.macro_repository import MacroRepository
from app.models.macro import MacroTopic, GlobalNews, GlobalHourlyReport
from app.services.macro_ai_service import MacroAIService
from app.services.macro_fetcher import MacroFetcher
from app.services.macro_notifier import MacroNotifier

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
    async def update_global_radar(db: AsyncSession = None, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """
        [业务入口] 抓取并持久化宏观雷达热点。
        支持后台异步调用（db 为空时自动创建会话）。
        """
        if db is None:
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_global_radar_internal(new_db, api_key_siliconflow)
        return await MacroService._update_global_radar_internal(db, api_key_siliconflow)

    @staticmethod
    async def _update_global_radar_internal(db: AsyncSession, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """
        [核心逻辑] 宏观雷达更新：
        1. 调用 Tavily 搜索全球最新宏观动态。
        2. 如果搜索失败，回退利用近期数据库已有快讯。
        3. 调用 AI 解析新闻，提炼出【逻辑链】、【利好标的】和【利空标的】。
        4. 持久化并触发用户通知。
        """
        logger.info("Starting global macro radar update...")
        repo = MacroService._repo(db)
        try:
            # 1. 抓取全球实时宏观动态 (Tavily Provider)
            all_news_raw = await MacroFetcher.fetch_radar_news()
            
            # 2. 容错兜底：若抓取失败，则利用本地已有的最新快讯进行分析
            if not all_news_raw:
                all_news_raw = await repo.get_recent_news_for_radar()
            
            if not all_news_raw:
                logger.error("No external or local news available for macro radar update.")
                return []

            logger.info(f"Data source ready. Proceeding to AI analyzer with {len(all_news_raw)} items...")
            
            # 3. AI 深度解析：产出结构化的宏观主题
            topics_data = await MacroAIService.analyze_radar_topics(all_news_raw, db, api_key_siliconflow)
            
            if not topics_data:
                return []

            # 4. 数据落地 (Upsert 模式确保不重复添加相同主题)
            new_topics = await repo.upsert_topics(topics_data)
            
            # 5. 推送提醒：根据用户订阅状态分发飞书/终端通知
            users = await repo.get_macro_alert_users()
            logger.info(f"Successfully processed {len(new_topics)} macro topics (Upsert).")
            await MacroNotifier.notify_topics(users, new_topics)
            
            return new_topics

        except Exception as e:
            logger.error(f"Macro AI processing failed: {e}")
            await repo.rollback()
            return []

    @staticmethod
    async def get_latest_radar(db: AsyncSession) -> List[MacroTopic]:
        """获取最新的宏观雷达主题（用于前端瀑布流展示）"""
        return await MacroService._repo(db).get_latest_topics()

    @staticmethod
    async def update_cls_news(db: AsyncSession = None) -> List[GlobalNews]:
        """
        [业务入口] 抓取并持久化财联社全球快讯。
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
        """别名：更新快讯头条"""
        return await MacroService.update_settings(db)

    @staticmethod
    async def generate_global_hourly_report(db: AsyncSession) -> GlobalHourlyReport | None:
        """
        [定时任务逻辑] 每整点汇总过去 1 小时快讯，生成一份全局宏观综述报告：
        1. 提取核心摘要。
        2. 计算整体市场情绪（看多/看空/中性）。
        3. 构建影响图谱（Ticker -> 影响逻辑映射）。
        """
        repo = MacroService._repo(db)
        news_items = await repo.get_recent_news_for_hourly_report()
        if not news_items:
            return None

        now = datetime.utcnow()
        hour_key = now.strftime("%Y-%m-%d-%H")

        # 缓存检查：同一小时不再重复生成
        existing_report = await repo.get_hourly_report(hour_key)
        if existing_report:
            logger.info(f"Global hourly report for {hour_key} already exists. Skipping AI call.")
            return existing_report

        try:
            # 调用 AI 生成高度压缩的精要总结
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
        [用户接口] 生成个性化的整点新闻总结：
        1. 获取或生成当前小时的全局宏观报告。
        2. 读取用户的持仓标的 (Portfolio)。
        3. 将全局“影响图谱”与用户持仓进行碰撞，实现【持仓穿透分析】。
        """
        # 1. 获取全局报告基准
        global_report = await MacroService.generate_global_hourly_report(db)
        if not global_report:
            return {"summary": "本小时暂无关键新闻或 AI 分析正在生成中。", "count": 0}

        # 2. 获取用户持仓数据 (仅 Ticker 列表)
        user_tickers = await MacroService._repo(db).get_user_portfolio_tickers(user_id)

        # 3. 执行个性化过滤：筛选出影响到用户持仓的条目
        personalized_impact = []
        impact_map = global_report.impact_map or {}
        
        for ticker, reason in impact_map.items():
            if ticker in user_tickers:
                personalized_impact.append(f"**{ticker}**: {reason}")

        # 4. 拼装多级总结内容
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
        """获取最新的快讯列表（用于前端时间线展示）"""
        return await MacroService._repo(db).get_latest_news(limit=limit)
