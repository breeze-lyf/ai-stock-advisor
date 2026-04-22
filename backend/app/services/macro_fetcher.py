import asyncio
import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MacroFetcher:
    """
    【宏观数据抓取器 (Macro Fetcher)】
    负责从多个数据源获取原始新闻和宏观事件。
    - 国内宏观视角：AkShare 东财/同花顺全球快讯 (中文，A股关联性强)
    - 美股市场情绪：yfinance SPY/QQQ/^VIX/^TNX 新闻 (覆盖大盘、科技、恐慌、利率四大定价因子)
    - 权威政策信号：RSS 美联储官方 / CNBC经济 / MarketWatch 实时标题
    - 国内快讯：AkShare 财联社电报，获取高频市场动态。
    """

    @staticmethod
    async def fetch_radar_news() -> list[dict[str, Any]]:
        """
        【多源免费数据管道】并发聚合三层信号，任一来源失败不影响整体。

        数据层次设计：
        1. 国内宏观视角：AkShare 东财全球快讯 → A股相关性强的中文宏观信号
        2. 美股市场情绪：yfinance 核心指数新闻 → SPY/QQQ/VIX/10Y利率定价信号
        3. 权威政策信号：RSS 美联储/CNBC/MarketWatch → 货币政策与宏观政策原始源头
        """
        results = await asyncio.gather(
            MacroFetcher._fetch_akshare_global_news(),
            MacroFetcher._fetch_yfinance_market_news(),
            MacroFetcher._fetch_rss_news(),
            return_exceptions=True,
        )

        all_news: list[dict[str, Any]] = []
        source_labels = ["AkShare东财", "yfinance市场", "RSS权威源"]
        for label, result in zip(source_labels, results):
            if isinstance(result, Exception):
                logger.warning(f"[MacroFetcher] {label} 抓取失败: {result}")
            elif result:
                all_news.extend(result)
                logger.info(f"[MacroFetcher] {label}: {len(result)} 条")

        logger.info(f"[MacroFetcher] 多源雷达合并完成，共 {len(all_news)} 条原始数据")
        return all_news

    @staticmethod
    async def _fetch_akshare_global_news() -> list[dict[str, Any]]:
        """
        东方财富/同花顺全球快讯 (AkShare)，无需 API Key。
        两个接口互为容错，有数据即停，避免重复。
        """
        def _sync() -> list[dict[str, Any]]:
            import akshare as ak
            items: list[dict[str, Any]] = []
            for func_name, source_label in [
                ("stock_info_global_em", "东财"),
                ("stock_info_global_ths", "同花顺"),
            ]:
                try:
                    df = getattr(ak, func_name)()
                    if df is None or df.empty:
                        continue
                    for _, row in df.head(20).iterrows():
                        # AkShare 各接口列名不统一，做多字段容错
                        title = str(
                            row.get("标题") or row.get("title") or row.get("新闻标题") or ""
                        ).strip()
                        content = str(
                            row.get("内容") or row.get("content") or row.get("摘要") or title
                        ).strip()
                        if not title or title == "nan":
                            continue
                        items.append({
                            "title": title,
                            "content": content[:400],
                            "url": str(row.get("链接") or row.get("url") or ""),
                            "source": source_label,
                        })
                    if items:
                        break  # 有数据则不再尝试备用源
                except Exception as e:
                    logger.debug(f"AkShare {func_name} failed: {e}")
            return items

        return await asyncio.to_thread(_sync)

    @staticmethod
    async def _fetch_yfinance_market_news() -> list[dict[str, Any]]:
        """
        yfinance 核心市场情绪指标新闻。

        四大定价因子覆盖：
        - SPY：大盘整体情绪
        - QQQ：科技/成长股叙事
        - ^VIX：市场恐慌指数，风险情绪晴雨表
        - ^TNX：10年期美债利率，股债博弈核心变量
        """
        MARKET_TICKERS = ["SPY", "QQQ", "^VIX", "^TNX"]

        def _sync_fetch_all() -> list[dict[str, Any]]:
            import yfinance as yf
            items: list[dict[str, Any]] = []
            seen_titles: set[str] = set()
            for symbol in MARKET_TICKERS:
                try:
                    raw_news = getattr(yf.Ticker(symbol), "news", None) or []
                    for entry in raw_news[:6]:
                        content_obj = entry.get("content") or {}
                        title = (content_obj.get("title") or entry.get("title") or "").strip()
                        summary = (content_obj.get("summary") or entry.get("summary") or "").strip()
                        url = (
                            content_obj.get("canonicalUrl", {}).get("url")
                            or content_obj.get("clickThroughUrl", {}).get("url")
                            or entry.get("link") or ""
                        )
                        if not title or title in seen_titles:
                            continue
                        seen_titles.add(title)
                        items.append({
                            "title": title,
                            "content": summary[:400] or title,
                            "url": url,
                            "source": f"yfinance/{symbol}",
                        })
                except Exception as e:
                    logger.debug(f"yfinance news fetch for {symbol} failed: {e}")
            return items

        return await asyncio.to_thread(_sync_fetch_all)

    @staticmethod
    async def _fetch_rss_news() -> list[dict[str, Any]]:
        """
        RSS 权威信源：美联储官方 + CNBC经济频道 + MarketWatch 实时标题。
        feedparser 解析，无需 API Key，提供最高权威度的政策原始信号。
        """
        RSS_FEEDS = [
            ("https://www.federalreserve.gov/feeds/press_all.xml", "美联储", 5),
            (
                "https://search.cnbc.com/rs/search/combinedcms/view.xml"
                "?partnerId=wrss01&id=100003114",
                "CNBC经济",
                8,
            ),
            (
                "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
                "MarketWatch",
                8,
            ),
        ]

        def _sync_parse_all() -> list[dict[str, Any]]:
            try:
                import feedparser
            except ImportError:
                logger.warning("[MacroFetcher] feedparser 未安装，RSS 源跳过。请执行: pip install feedparser")
                return []

            items: list[dict[str, Any]] = []
            for feed_url, source_name, max_items in RSS_FEEDS:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:max_items]:
                        title = (getattr(entry, "title", "") or "").strip()
                        raw_summary = (
                            getattr(entry, "summary", "")
                            or getattr(entry, "description", "")
                            or title
                        )
                        # 清除 HTML 标签
                        summary_clean = re.sub(r"<[^>]+>", "", raw_summary).strip()
                        link = getattr(entry, "link", "") or ""
                        if not title:
                            continue
                        items.append({
                            "title": title,
                            "content": summary_clean[:400] or title,
                            "url": link,
                            "source": source_name,
                        })
                except Exception as e:
                    logger.debug(f"RSS fetch for {source_name} failed: {e}")
            return items

        return await asyncio.to_thread(_sync_parse_all)

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
            
            # 【幂等性指纹逻辑】
            # 使用“发布时间+内容”计算 MD5 防重，确保即使新闻源因网络波动被重复抓取，
            # 数据库层面也不会产生脏数据，保证宏观分析的唯一性和精准性。
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
