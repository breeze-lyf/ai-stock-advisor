from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.macro_repository import MacroRepository


class MacroPersistence:
    """
    【宏观持久化门面 (Macro Persistence Facade)】
    该类作为业务逻辑层 (Services) 与数据访问层 (Repositories) 之间的中转站。
    负责协调数据库会话，执行宏观主题、新闻快讯和整点报告的存取操作。
    """
    @staticmethod
    def _default_impact_analysis():
        """返回默认的影响分析模版。"""
        return MacroRepository.default_impact_analysis()

    @staticmethod
    async def upsert_topics(db: AsyncSession, topics_data):
        """更新或插入宏观雷达主题（包含热度、逻辑链等）。"""
        return await MacroRepository(db).upsert_topics(topics_data)

    @staticmethod
    async def persist_cls_news(db: AsyncSession, news_items):
        """将抓取到的财联社快讯持久化到数据库。"""
        return await MacroRepository(db).persist_cls_news(news_items)

    @staticmethod
    async def get_latest_topics(db: AsyncSession, limit: int = 10):
        """获取最新的 N 条宏观主题。"""
        return await MacroRepository(db).get_latest_topics(limit=limit)

    @staticmethod
    async def get_latest_news(db: AsyncSession, limit: int = 50):
        """获取最新的 N 条宏观快讯。"""
        return await MacroRepository(db).get_latest_news(limit=limit)

    @staticmethod
    async def get_recent_news_for_radar(db: AsyncSession, hours: int = 24, limit: int = 30) -> list[dict]:
        """为 AI 雷达分析获取最近 X 小时内的代表性新闻。"""
        return await MacroRepository(db).get_recent_news_for_radar(hours=hours, limit=limit)

    @staticmethod
    async def get_recent_news_for_hourly_report(db: AsyncSession, hours: int = 1):
        """获取过去一小时内的新闻，用于生成整点精要。"""
        return await MacroRepository(db).get_recent_news_for_hourly_report(hours=hours)

    @staticmethod
    async def get_hourly_report(db: AsyncSession, hour_key: str):
        """根据整点 Key (如 20240317-14) 获取已生成的报告。"""
        return await MacroRepository(db).get_hourly_report(hour_key)

    @staticmethod
    async def get_or_create_hourly_report(db: AsyncSession, hour_key: str, parsed_report: dict | None, news_count: int):
        """获取或创建整点报告（保证幂等性）。"""
        return await MacroRepository(db).get_or_create_hourly_report(hour_key, parsed_report, news_count)

    @staticmethod
    async def get_user_portfolio_tickers(db: AsyncSession, user_id: str) -> set[str]:
        """获取用户当前所有持仓标的代码，用于“持仓穿透”分析。"""
        return await MacroRepository(db).get_user_portfolio_tickers(user_id)

    @staticmethod
    async def get_macro_alert_users(db: AsyncSession):
        """获取开启了宏观预警通知的所有用户列表。"""
        return await MacroRepository(db).get_macro_alert_users()
