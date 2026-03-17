import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.schemas.market_data import FullMarketData, ProviderFundamental, ProviderTechnical
from app.services.market_providers import ProviderFactory

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    @staticmethod
    async def fetch_from_providers(
        ticker: str,
        preferred_source: str,
        price_only: bool = False,
        skip_news: bool = False,
    ) -> Optional[FullMarketData]:
        provider = ProviderFactory.get_provider(ticker, preferred_source)

        if price_only:
            try:
                quote = await provider.get_quote(ticker)
                if quote:
                    return FullMarketData(quote=quote)
            except Exception as exc:
                logger.error(f"Price only fetch failed for {ticker}: {exc}")
                return None

        result = await provider.get_full_data(ticker)
        if result:
            return result

        try:
            quote_task = asyncio.create_task(provider.get_quote(ticker))
            fundamental_task = None
            indicator_task = None
            news_tasks = []

            if not price_only:
                fundamental_task = asyncio.create_task(provider.get_fundamental_data(ticker))
                indicator_task = asyncio.create_task(provider.get_historical_data(ticker, period="200d"))

                from app.services.market_providers.tavily import TavilyProvider

                tavily = TavilyProvider()
                news_tasks = [asyncio.create_task(provider.get_news(ticker))]

                if not skip_news and tavily.api_key:
                    news_tasks.append(asyncio.create_task(tavily.get_news(ticker)))

                is_us = not (ticker.isdigit() and len(ticker) == 6)

            core_tasks = [quote_task]
            if indicator_task:
                core_tasks.append(indicator_task)

            try:
                core_res = await asyncio.wait_for(
                    asyncio.gather(*core_tasks, return_exceptions=True),
                    timeout=15.0,
                )
                if len(core_tasks) == 2:
                    quote, indicators = core_res
                else:
                    quote, indicators = core_res[0], None
            except asyncio.TimeoutError:
                logger.warning(f"{ticker} 核心报价/指标抓取超时 (15s)")
                quote, indicators = None, None
            except Exception as exc:
                logger.error(f"{ticker} 核心抓取异常: {exc}")
                quote, indicators = None, None

            fundamental = None
            if fundamental_task:
                fundamental = await MarketDataFetcher._build_fundamental(provider, ticker, fundamental_task)

            news = await MarketDataFetcher._collect_news(ticker, news_tasks)

            if quote and not isinstance(quote, Exception):
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators)
                    if not isinstance(indicators, Exception) and indicators
                    else None,
                    news=news,
                )
        except Exception as exc:
            logger.error(f"从 {type(provider).__name__} 获取 {ticker} 数据时发生错误: {exc}")


        return None

    @staticmethod
    async def _build_fundamental(provider, ticker: str, fundamental_task):
        try:
            valuation_task = asyncio.create_task(provider.get_valuation_percentiles(ticker))
            flow_task = asyncio.create_task(provider.get_capital_flow(ticker))
            f_res, val_data, flow_data = await asyncio.gather(
                fundamental_task,
                valuation_task,
                flow_task,
                return_exceptions=True,
            )

            if isinstance(f_res, Exception) or not f_res:
                fundamental = ProviderFundamental()
                logger.info(f"{ticker} main fundamental task failed, creating empty container for quant metrics")
            else:
                fundamental = f_res

            if not isinstance(val_data, Exception) and val_data:
                fundamental.pe_percentile = val_data.get("pe_percentile")
                fundamental.pb_percentile = val_data.get("pb_percentile")

            if not isinstance(flow_data, Exception) and flow_data:
                fundamental.net_inflow = flow_data.get("net_inflow")

            if all(getattr(fundamental, field) is None for field in fundamental.model_fields):
                return None
            return fundamental
        except Exception as exc:
            logger.error(f"{ticker} 增强基本面异常: {exc}")
            return None

    @staticmethod
    async def _collect_news(ticker: str, news_tasks) -> list:
        news = []
        if not news_tasks:
            return news

        try:
            news_res = await asyncio.wait_for(
                asyncio.gather(*news_tasks, return_exceptions=True),
                timeout=2.0,
            )
            seen_links = set()
            for result in news_res:
                if isinstance(result, list):
                    for item in result:
                        if item.link and item.link not in seen_links:
                            news.append(item)
                            seen_links.add(item.link)
                elif isinstance(result, Exception) and "432" in str(result):
                    logger.warning(
                        f"Tavily news for {ticker} returned 432 error, likely rate limit or invalid query. Skipping."
                    )
                elif isinstance(result, Exception):
                    logger.warning(f"News task for {ticker} failed with: {result}")

            def sort_key(item):
                publish_time = item.publish_time if item.publish_time else datetime.utcnow()
                if publish_time.tzinfo is not None:
                    publish_time = publish_time.replace(tzinfo=None)
                return publish_time

            news.sort(key=sort_key, reverse=True)
        except asyncio.TimeoutError:
            logger.warning(f"{ticker} 新闻抓取超时 (1.5s)，已忽略")
        except Exception as exc:
            logger.warning(f"{ticker} 新闻处理异常: {exc}")
        return news
