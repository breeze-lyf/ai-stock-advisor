from __future__ import annotations
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.macro import GlobalHourlyReport, GlobalNews, MacroTopic
from app.models.portfolio import Portfolio
from app.models.user import User
from app.utils.time import utc_now_naive


class MacroRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def default_impact_analysis():
        return {
            "logic": "逻辑正在实时推演中...",
            "beneficiaries": [],
            "detriments": [],
        }

    async def upsert_topics(self, topics_data):
        new_topics = []
        for topic_data in topics_data:
            title = topic_data.get("title")
            stmt = select(MacroTopic).where(MacroTopic.title == title)
            result = await self.db.execute(stmt)
            existing_topic = result.scalar_one_or_none()

            impact_analysis = {
                "logic": topic_data.get("logic"),
                "beneficiaries": topic_data.get("beneficiaries", []),
                "detriments": topic_data.get("detriments", []),
                "time_layer": topic_data.get("time_layer", "narrative"),
                "market_pulse": topic_data.get("market_pulse", {}),
            }
            if not impact_analysis:
                impact_analysis = self.default_impact_analysis()

            if existing_topic:
                existing_topic.summary = topic_data.get("summary")
                existing_topic.heat_score = topic_data.get("heat_score", 50.0)
                existing_topic.impact_analysis = impact_analysis
                existing_topic.source_links = topic_data.get("sources", [])
                existing_topic.updated_at = utc_now_naive()
                new_topics.append(existing_topic)
                continue

            topic = MacroTopic(
                title=title,
                summary=topic_data.get("summary"),
                heat_score=topic_data.get("heat_score", 50.0),
                impact_analysis=impact_analysis,
                source_links=topic_data.get("sources", []),
            )
            self.db.add(topic)
            new_topics.append(topic)

        await self.db.commit()
        for topic in new_topics:
            try:
                await self.db.refresh(topic)
            except Exception:
                pass
        return new_topics

    async def persist_cls_news(self, news_items):
        new_items = []
        for item in news_items:
            stmt = select(GlobalNews).where(GlobalNews.fingerprint == item["fingerprint"])
            existing = await self.db.execute(stmt)
            if existing.scalar_one_or_none():
                continue

            news_item = GlobalNews(
                published_at=item["published_at"],
                title=item["title"],
                content=item["content"],
                fingerprint=item["fingerprint"],
            )
            self.db.add(news_item)
            new_items.append(news_item)

        if new_items:
            await self.db.commit()
        return new_items

    async def get_latest_topics(self, limit: int = 10):
        stmt = select(MacroTopic).order_by(MacroTopic.updated_at.desc(), MacroTopic.heat_score.desc()).limit(limit)
        result = await self.db.execute(stmt)
        topics = list(result.scalars().all())
        for topic in topics:
            if not topic.impact_analysis:
                topic.impact_analysis = self.default_impact_analysis()
        return topics

    async def get_latest_news(self, limit: int = 50):
        stmt = select(GlobalNews).order_by(GlobalNews.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_news_for_radar(self, hours: int = 24, limit: int = 30) -> list[dict]:
        cutoff = utc_now_naive() - timedelta(hours=hours)
        stmt = (
            select(GlobalNews)
            .where(GlobalNews.created_at >= cutoff)
            .order_by(GlobalNews.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        fallback_news = result.scalars().all()
        return [
            {"title": news.title, "content": news.content, "source": "Local-Fallback"}
            for news in fallback_news
        ]

    async def get_recent_news_for_hourly_report(self, hours: int = 1):
        cutoff = utc_now_naive() - timedelta(hours=hours)
        stmt = select(GlobalNews).where(GlobalNews.created_at >= cutoff).order_by(GlobalNews.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_hourly_report(self, hour_key: str):
        stmt = select(GlobalHourlyReport).where(GlobalHourlyReport.hour_key == hour_key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_hourly_report(self, hour_key: str, parsed_report: dict | None, news_count: int):
        existing_report = await self.get_hourly_report(hour_key)
        if existing_report:
            return existing_report, True

        if not parsed_report:
            return None, False

        new_report = GlobalHourlyReport(
            hour_key=hour_key,
            core_summary=parsed_report.get("core_summary", ""),
            sentiment=parsed_report.get("sentiment", "中性"),
            impact_map=parsed_report.get("impact_map", {}),
            news_count=news_count,
        )
        self.db.add(new_report)
        await self.db.commit()
        return new_report, False

    async def get_user_portfolio_tickers(self, user_id: str) -> set[str]:
        stmt = select(Portfolio.ticker).where(Portfolio.user_id == user_id, Portfolio.quantity > 0)
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def get_macro_alert_users(self):
        stmt = select(User).where(
            User.feishu_webhook_url != None,
            User.enable_macro_alerts == True,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def rollback(self):
        await self.db.rollback()
