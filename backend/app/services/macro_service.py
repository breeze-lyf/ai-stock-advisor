import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json
import re
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.services.market_providers.tavily import TavilyProvider
from app.services.ai_service import AIService
from app.models.macro import MacroTopic, GlobalNews

logger = logging.getLogger(__name__)

class MacroService:
    @staticmethod
    async def update_global_radar(db: AsyncSession = None, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """抓取并持久化宏观雷达热点 (支持后台安全模式)"""
        if db is None:
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_global_radar_internal(new_db, api_key_siliconflow)
        return await MacroService._update_global_radar_internal(db, api_key_siliconflow)

    @staticmethod
    async def _update_global_radar_internal(db: AsyncSession, api_key_siliconflow: str = None) -> List[MacroTopic]:
        """具体的热点更新逻辑实现"""
        logger.info("Starting global macro radar update...")
        
        # 1. 使用 Tavily 抓取当前最具市场影响力的 3-5 个新闻主题
        tavily = TavilyProvider()
        if not tavily.api_key:
            logger.warning("Tavily API key not configured, macro radar update skipped.")
            return []

        # 搜索宏观热点
        # 搜索词增强：聚焦于“影响市场”的宏观事件
        queries = [
            "top global macro economic events moving markets today",
            "major geopolitical conflicts impacting stock market",
            "Fed interest rate expectations and market impact news"
        ]
        
        all_news_raw = []
        for q in queries:
            try:
                # 借用 get_news 的结构，但我们可以直接调用 tavily 的原始 post 以获得更广的搜索
                async with tavily._semaphore:
                    import httpx
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        payload = {
                            "api_key": tavily.api_key,
                            "query": q,
                            "topic": "news",
                            "search_depth": "advanced",
                            "max_results": 8
                        }
                        resp = await client.post(tavily.base_url, json=payload)
                        resp.raise_for_status()
                        all_news_raw.extend(resp.json().get("results", []))
            except Exception as e:
                logger.error(f"Macro search failed for query '{q}': {e}")

        if not all_news_raw:
            logger.warning("Tavily returned 0 news results for all macro queries.")
            return []

        logger.info(f"Fetched {len(all_news_raw)} news items from Tavily. Proceeding to AI analyzer...")
        
        # 2. 调用 AI 进行主题聚类与传导逻辑推演
        # 我们给 AI 一堆杂乱的新闻，让它提炼出 3 个最核心的主题
        news_context = "\n".join([f"- {n.get('title')}: {n.get('content')[:200]}" for n in all_news_raw])
        
        prompt = f"""
        你是一位全球宏观策略首席分析师。请从以下新闻片段中提炼出当前对全球股市（特别是美股）影响最大的 3 个宏观主题。
        
        新闻背景:
        {news_context}
        
        对于每个主题，请执行以下深度分析：
        1. 核心逻辑 (Logic Chain): 事件是如何传导并影响市场的。
        2. 利好标的 (Beneficiaries): 哪些板块、指数或具体美股标的受益，并给出理由。
        3. 利空标的 (Detriments): 哪些板块或标的受损，并给出理由。
        4. 热度评分 (Heat Score): 0-100 评分。
        
        请严格返回以下 JSON 格式：
        {{
          "topics": [
            {{
              "title": "主题标题",
              "summary": "简短背景总结",
              "heat_score": 85,
              "logic": "逻辑链条描述",
              "beneficiaries": [
                {{"ticker": "代码", "reason": "利好路由"}}
              ],
              "detriments": [
                {{"ticker": "代码", "reason": "利空理由"}}
              ],
              "sources": ["url1", "url2"]
            }}
          ]
        }}
        """
        
        try:
            # 这里的 AI 调用我们使用 SiliconFlow (DeepSeek/Qwen)
            # 如果未传入 key，则尝试从系统配置中获取
            final_api_key = api_key_siliconflow or settings.SILICONFLOW_API_KEY
            if not final_api_key:
                logger.error("No SiliconFlow API key provided for macro update.")
                return []

            ai_response = await AIService.call_siliconflow(
                prompt=prompt,
                api_key=final_api_key,
                model="deepseek-v3",
                db=db
            )
            
            # 解析 JSON
            json_match = re.search(r'(\{.*\})', ai_response, re.DOTALL)
            if not json_match:
                logger.error("Failed to extract JSON from AI macro response")
                return []
                
            data = json.loads(json_match.group(1))
            topics_data = data.get("topics", [])
            
            # 3. 持久化到数据库
            new_topics = []
            for t_data in topics_data:
                topic = MacroTopic(
                    title=t_data.get("title"),
                    summary=t_data.get("summary"),
                    heat_score=t_data.get("heat_score", 50.0),
                    impact_analysis={
                        "logic": t_data.get("logic"),
                        "beneficiaries": t_data.get("beneficiaries", []),
                        "detriments": t_data.get("detriments", [])
                    },
                    source_links=t_data.get("sources", [])
                )
                db.add(topic)
                new_topics.append(topic)
            
            # 清理旧热点（可选，保留最近 24 小时的即可）
            # ...
            
            await db.commit()
            logger.info(f"Successfully updated {len(new_topics)} macro topics.")
            return new_topics

        except Exception as e:
            logger.error(f"Macro AI processing failed: {e}")
            await db.rollback()
            return []

    @staticmethod
    async def get_latest_radar(db: AsyncSession) -> List[MacroTopic]:
        """获取最新的宏观雷达数据 (按热度优先 + 时间辅助)"""
        stmt = select(MacroTopic).order_by(MacroTopic.heat_score.desc(), MacroTopic.updated_at.desc()).limit(10)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_cls_news(db: AsyncSession = None) -> List[GlobalNews]:
        """抓取并持久化财联社全球快讯 (支持后台安全模式)"""
        if db is None:
            # 如果没传 db，说明是作为 BackgroundTasks 运行，需自己启 Session
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_cls_news_internal(new_db)
        return await MacroService._update_cls_news_internal(db)

    @staticmethod
    async def _update_cls_news_internal(db: AsyncSession) -> List[GlobalNews]:
        """抓取并持久化财联社全球快讯的内部实现"""
        logger.info("Starting Cailianshe global news update (Thread Safe)...")
        try:
            # 1. 使用 to_thread 异步化同步库调用，防止阻塞 FastAPI 事件循环
            def fetch_from_akshare():
                import akshare as ak
                return ak.stock_info_global_cls()
            
            news_df = await asyncio.to_thread(fetch_from_akshare)
            
            if news_df is None or news_df.empty:
                logger.warning("Cailianshe update returned empty data.")
                return []
                
            recent_news = news_df.head(50)
            new_items = []
            
            for _, row in recent_news.iterrows():
                published_at = str(row.get('发布时间', ''))
                title = str(row.get('标题', ''))
                content = str(row.get('内容', ''))
                
                if not content: continue
                
                # 生成唯一指纹排重
                fingerprint = hashlib.md5(f"{published_at}{content}".encode()).hexdigest()
                
                # 检查是否已存在
                stmt = select(GlobalNews).where(GlobalNews.fingerprint == fingerprint)
                existing = await db.execute(stmt)
                if existing.scalar_one_or_none():
                    continue
                    
                news_item = GlobalNews(
                    published_at=published_at,
                    title=title,
                    content=content,
                    fingerprint=fingerprint
                )
                db.add(news_item)
                new_items.append(news_item)
                
            if new_items:
                await db.commit()
                logger.info(f"Successfully persisted {len(new_items)} new Cailianshe items.")
            
            return new_items
        except Exception as e:
            logger.error(f"Failed to update Cailianshe news: {e}")
            await db.rollback()
            return []

    @staticmethod
    async def get_latest_news(db: AsyncSession, limit: int = 50) -> List[GlobalNews]:
        """从数据库获取最新的全球快讯"""
        stmt = select(GlobalNews).order_by(GlobalNews.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
