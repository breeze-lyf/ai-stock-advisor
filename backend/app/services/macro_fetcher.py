import asyncio
import hashlib
import logging
from typing import Any
from app.services.market_providers.tavily import TavilyProvider

logger = logging.getLogger(__name__)


class MacroFetcher:
    """
    【宏观数据抓取器 (Macro Fetcher)】
    负责从多个数据源获取原始新闻和宏观事件。
    - 全球视角：使用 Tavily (Search API) 抓取美股及全球宏观新闻。
    - 国内快讯：使用 AkShare 抓取财联社电报，获取高频市场动态。
    """
    @staticmethod
    async def fetch_radar_news() -> list[dict[str, Any]]:
        """
        获取宏观雷达所需的高质量全球新闻。
        通过 TavilyProvider 执行定向深度搜索。
        """
        tavily = TavilyProvider()
        if not tavily.api_key:
            logger.warning("Tavily API key not configured, macro radar update skipped.")
            return []

        # 精确定义的宏观搜索关键词，旨在捕获市场波动源
        queries = [
            "top global macro economic events moving markets today",
            "major geopolitical conflicts impacting stock market",
            "Fed interest rate expectations and market impact news",
        ]

        all_news_raw = []
        for query in queries:
            try:
                # 使用信号量控制并发压力
                async with tavily._semaphore:
                    import httpx
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        payload = {
                            "api_key": tavily.api_key,
                            "query": query,
                            "topic": "news",
                            "search_depth": "advanced",
                            "max_results": 8,
                        }
                        response = await client.post(tavily.base_url, json=payload)
                        response.raise_for_status()
                        all_news_raw.extend(response.json().get("results", []))
            except Exception as exc:
                logger.error(f"Macro search failed for query '{query}': {exc}")
        return all_news_raw

    @staticmethod
    async def fetch_cls_news_rows():
        """
        异步封装：从财联社抓取实时快讯 (AkShare)。
        底层调用 ak.stock_info_global_cls()。
        """
        def fetch_from_akshare():
            import akshare as ak
            return ak.stock_info_global_cls()

        # 将同步的阻塞 IO (AkShare) 放到线程池执行，避免阻塞事件循环
        return await asyncio.to_thread(fetch_from_akshare)

    @staticmethod
    def build_news_items_from_df(news_df):
        """
        数据清洗与去重指纹计算。
        将 AkShare 返回的 DataFrame 转换为标准化的字典列表。
        """
        if news_df is None or news_df.empty:
            return []

        news_items = []
        recent_news = news_df.head(50)
        for _, row in recent_news.iterrows():
            published_at = str(row.get("发布时间", ""))
            title = str(row.get("标题", ""))
            content = str(row.get("内容", ""))
            if not content:
                continue
            # 计算内容指纹：用于后续入库时的幂等性校验
            fingerprint = hashlib.md5(f"{published_at}{content}".encode()).hexdigest()
            news_items.append(
                {
                    "published_at": published_at,
                    "title": title,
                    "content": content,
                    "fingerprint": fingerprint,
                }
            )
        return news_items
