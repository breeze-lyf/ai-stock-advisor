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
from app.models.user import User
from app.services.notification_service import NotificationService

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
            logger.warning("Tavily returned 0 results or Quota Exceeded. Falling back to local GlobalNews...")
            # 降级方案：从数据库中提取过去 24 小时内的财联社全球快讯
            one_day_ago = datetime.utcnow() - timedelta(hours=24)
            stmt = select(GlobalNews).where(GlobalNews.created_at >= one_day_ago).order_by(GlobalNews.created_at.desc()).limit(30)
            res = await db.execute(stmt)
            fallback_news = res.scalars().all()
            
            if not fallback_news:
                logger.error("No local news available for fallback. Macro radar update aborted.")
                return []
                
            all_news_raw = [{"title": n.title, "content": n.content, "source": "Local-Fallback"} for n in fallback_news]
            logger.info(f"Fallback successful: loaded {len(all_news_raw)} local news items for AI analysis.")

        logger.info(f"Data source ready. Proceeding to AI analyzer with {len(all_news_raw)} items...")
        
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
            
            # 3. 持久化到数据库 (实现 Upsert 逻辑)
            new_topics = []
            for t_data in topics_data:
                title = t_data.get("title")
                # 检查是否已存在同名主题（防止重复沉积）
                stmt = select(MacroTopic).where(MacroTopic.title == title)
                res = await db.execute(stmt)
                existing_topic = res.scalar_one_or_none()
                
                if existing_topic:
                    # 更新旧主题的内容与时间戳，使其“保鲜”
                    existing_topic.summary = t_data.get("summary")
                    existing_topic.heat_score = t_data.get("heat_score", 50.0)
                    existing_topic.impact_analysis = {
                        "logic": t_data.get("logic"),
                        "beneficiaries": t_data.get("beneficiaries", []),
                        "detriments": t_data.get("detriments", [])
                    }
                    existing_topic.source_links = t_data.get("sources", [])
                    existing_topic.updated_at = datetime.utcnow()
                    new_topics.append(existing_topic)
                    logger.info(f"Updated existing macro topic: {title}")
                else:
                    # 插入全新的主题
                    topic = MacroTopic(
                        title=title,
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
                    logger.info(f"Inserted new macro topic: {title}")
            
            await db.commit()
            # 必须刷新对象以获取最新的 updated_at
            for nt in new_topics:
                try:
                    await db.refresh(nt)
                except:
                    pass
            logger.info(f"Successfully processed {len(new_topics)} macro topics (Upsert).")
            
            # --- 异步触发飞书预警 (Async Feishu Notification) ---
            if new_topics:
                # 1. 对高热度主题发送独立深度预警
                for topic in new_topics:
                    if topic.heat_score >= 90:
                        try:
                            asyncio.create_task(NotificationService.send_macro_alert(
                                title=topic.title,
                                summary=topic.summary,
                                heat_score=topic.heat_score
                            ))
                        except Exception as notify_e:
                            logger.error(f"Failed to trigger individual macro alert: {notify_e}")
                
                # 2. 发送本轮扫描汇总简报
                try:
                    asyncio.create_task(NotificationService.send_macro_summary(
                        topics_count=len(new_topics),
                        topics_list=new_topics
                    ))
                except Exception as summary_e:
                    logger.error(f"Failed to trigger macro summary notification: {summary_e}")

            return new_topics

        except Exception as e:
            logger.error(f"Macro AI processing failed: {e}")
            await db.rollback()
            return []

    @staticmethod
    async def get_latest_radar(db: AsyncSession) -> List[MacroTopic]:
        """获取最新的宏观雷达数据 (按时间倒序优先，确保新鲜度)"""
        stmt = select(MacroTopic).order_by(MacroTopic.updated_at.desc(), MacroTopic.heat_score.desc()).limit(10)
        result = await db.execute(stmt)
        topics = list(result.scalars().all())
        
        # 数据填充：强制补全 impact_analysis 中的空字段，防止前端崩溃
        for t in topics:
            if not t.impact_analysis:
                t.impact_analysis = {
                    "logic": "逻辑正在实时推演中...",
                    "beneficiaries": [],
                    "detriments": []
                }
        return topics

    @staticmethod
    async def update_cls_news(db: AsyncSession = None) -> List[GlobalNews]:
        """抓取并持久化财联社全球快讯 (支持后台安全模式)"""
        if db is None:
            from app.core.database import SessionLocal
            async with SessionLocal() as new_db:
                return await MacroService._update_cls_news_internal(new_db)
        return await MacroService._update_cls_news_internal(db)

    @staticmethod
    async def _update_cls_news_internal(db: AsyncSession) -> List[GlobalNews]:
        """抓取并持久化财联社全球快讯的内部实现"""
        logger.info("Starting Cailianshe global news update (Standard Version)...")
        try:
            def fetch_from_akshare():
                import akshare as ak
                return ak.stock_info_global_cls()
            
            news_df = await asyncio.to_thread(fetch_from_akshare)
            
            if news_df is None or news_df.empty:
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
                logger.info(f"Successfully persisted {len(new_items)} news items.")
            
            return new_items
        except Exception as e:
            logger.error(f"Failed to update news: {e}")
            await db.rollback()
            return []

    @staticmethod
    async def generate_hourly_news_summary(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        汇总过去 1 小时内的全量财联社新闻标题，并由 AI 生成精要总结。
        用于飞书每小时定点推送。
        """
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        # 查询过去一小时内创建的新闻
        stmt = select(GlobalNews).where(GlobalNews.created_at >= one_hour_ago).order_by(GlobalNews.created_at.desc())
        result = await db.execute(stmt)
        news_items = result.scalars().all()
        
        if not news_items:
            return {"summary": "", "count": 0}
            
        # 1. 获取特定用户的真实持仓上下文 (仅限数量 > 0 的标的)
        from app.models.portfolio import Portfolio
        portfolio_stmt = select(Portfolio.ticker).where(
            Portfolio.user_id == user_id,
            Portfolio.quantity > 0
        )
        portfolio_res = await db.execute(portfolio_stmt)
        portfolio_tickers = list(set(portfolio_res.scalars().all()))
            
        portfolio_context = f"用户当前真实持仓列表: {', '.join(portfolio_tickers)}" if portfolio_tickers else "当前账户暂无任何持仓标的。"

        # 2. 构造标题列表
        titles = [f"- {n.title or n.content[:50]}" for n in news_items]
        content_for_ai = "\n".join(titles)
        
        prompt = f"""
        你是一位顶级对冲基金首席策略师。以下是过去一小时内发生的财联社新闻标题汇总：
        
        {content_for_ai}
        
        [持仓白名单] (仅限分析以下标的):
        {portfolio_context}
        
        请执行“三维度”深度研判任务：
        1. **【核心综述】**: 用 50 字内概括本小时最重要的 1-2 件核心驱动事件。
        2. **【逐条解析】**: 挑选 3-5 条关键消息，说明其对相关赛道或宏观因子的具体传导影响。
        3. **【持仓穿透】**: 针对[持仓白名单]中的标的，分别给出[利好/利空/震荡]判断及简短逻辑（必须显式列出标的代码）。
        
        [禁令]:
        - 严禁使用 # 或 ### 等 Markdown 标题字符。请使用 **【维度名称】** 这种加粗形式。
        - 严禁提及 [持仓白名单] 以外的任何具体股票代码。
        - 严禁提供任何具体的买卖交易动作建议。
        
        请以标准 JSON 格式返回，确保 summary 内部使用 Markdown 格式实现上述三个维度的清晰排版：
        {{
          "summary": "**【核心综述】**\\n内容...\\n\\n**【逐条解析】**\\n内容...\\n\\n**【持仓穿透】**\\n标的代码: [结论] - 原因...",
          "sentiment": "整体情绪定调"
        }}
        """
        
        try:
            ai_response = await AIService.call_siliconflow(
                prompt=prompt,
                model="deepseek-v3",
                api_key=settings.SILICONFLOW_API_KEY,
                db=db
            )
            
            # 解析 JSON
            import re
            json_match = re.search(r'(\{.*\})', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return {
                    "summary": data.get("summary", ""),
                    "count": len(news_items),
                    "sentiment": data.get("sentiment", "中性")
                }
            return {"summary": ai_response, "count": len(news_items)}
        except Exception as e:
            logger.error(f"Failed to generate hourly news summary: {e}")
            return {"summary": "AI 总结生成失败，请查看原始快讯。", "count": len(news_items)}

    @staticmethod
    async def get_latest_news(db: AsyncSession, limit: int = 50) -> List[GlobalNews]:
        """从数据库获取最新的全球快讯 (标准排序)"""
        stmt = select(GlobalNews).order_by(GlobalNews.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
