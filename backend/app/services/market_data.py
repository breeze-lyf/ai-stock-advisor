from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.models.stock import Stock, MarketDataCache, MarketStatus, StockNews
from app.services.market_providers import ProviderFactory
from app.schemas.market_data import FullMarketData, ProviderTechnical

logger = logging.getLogger(__name__)

# 市场数据分析中台：负责协调多个数据源、处理缓存逻辑并更新数据库
class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "YFINANCE", force_refresh: bool = False):
        """
        获取单支股票的实时/最新数据。
        策略：优先检查本地缓存 -> 缓存失效则从外部 API 抓取 -> 更新数据库。
        """
        # 1. 检查本地数据库缓存
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        # 如果不是强制刷新，且缓存时间在 1 分钟内，则直接返回缓存
        if not force_refresh and cache and (now - cache.last_updated) < timedelta(minutes=1):
            return cache

        # 2. 从数据提供商获取数据 (YFinance, AkShare 等)
        data = await MarketDataService._fetch_from_providers(ticker, preferred_source)

        # 3. 如果 API 请求失败且没有缓存，启用模拟模式（保证前端不报错）
        if not data:
            cache = await MarketDataService._handle_simulation(ticker, cache, now)
            await db.commit()
            return cache

        # 4. 将抓取到的数据更新到数据库中并返回
        return await MarketDataService._update_database(ticker, data, cache, db, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str) -> Optional[FullMarketData]:
        """
        根据策略调用不同的 Provider 来获取最全的股票数据
        """
        # 利用工厂模式获取对应的 Provider 实例
        provider = ProviderFactory.get_provider(ticker, preferred_source)
        
        # 尝试使用 Provider 预定义的“全量抓取”优化方法
        result = await provider.get_full_data(ticker)
        if result:
            return result

        # 如果没有一键抓取接口，则并行发起多个独立请求（报价、财务、指标、新闻）
        try:
            quote_task = provider.get_quote(ticker)
            fundamental_task = provider.get_fundamental_data(ticker)
            indicator_task = provider.get_historical_data(ticker, period="200d")
            
            # AI 新闻增强：如果配置了 Tavily，优先使用 AI 搜索获取高质量总结
            from app.services.market_providers.tavily import TavilyProvider
            tavily = TavilyProvider()
            news_task = tavily.get_news(ticker) if tavily.api_key else provider.get_news(ticker)
            
            # 使用 asyncio.gather 并行执行所有任务，提高效率
            res = await asyncio.gather(quote_task, fundamental_task, indicator_task, news_task, return_exceptions=True)
            quote, fundamental, indicators, news = res
            
            if not isinstance(quote, Exception) and quote:
                # 只要有了基础报价 (quote)，就认为本次抓取是成功的
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators) if not isinstance(indicators, Exception) and indicators else None,
                    news=news if not isinstance(news, Exception) else []
                )
        except Exception as e:
            logger.error(f"Error fetching from provider {type(provider).__name__} for {ticker}: {e}")

        # 兜底转换：如果首选源（如 AlphaVantage）失败，自动尝试使用 YFinance
        if preferred_source != "YFINANCE":
            yf_provider = ProviderFactory.get_provider(ticker, "YFINANCE")
            return await yf_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        """
        将 FullMarketData (Schema) 的数据持久化到数据库 (Models)
        """
        # 1. 确保 Stock 基础资料存在
        stock_stmt = select(Stock).where(Stock.ticker == ticker)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        
        if not stock:
            # 如果是第一次添加这支股票，初始化基础信息
            stock = Stock(ticker=ticker, name=data.quote.name or ticker)
            db.add(stock)
            await db.commit()
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()
        else:
            # 存在则按需更新名称
            if data.quote.name:
                stock.name = data.quote.name

        # 2. 更新财务基础面数据
        fundamental = data.fundamental
        if fundamental:
            stock.sector = fundamental.sector or stock.sector
            stock.industry = fundamental.industry or stock.industry
            stock.market_cap = fundamental.market_cap or stock.market_cap
            stock.pe_ratio = fundamental.pe_ratio or stock.pe_ratio
            stock.forward_pe = fundamental.forward_pe or stock.forward_pe
            stock.eps = fundamental.eps or stock.eps
            stock.dividend_yield = fundamental.dividend_yield or stock.dividend_yield
            stock.beta = fundamental.beta or stock.beta
            stock.fifty_two_week_high = fundamental.fifty_two_week_high or stock.fifty_two_week_high
            stock.fifty_two_week_low = fundamental.fifty_two_week_low or stock.fifty_two_week_low

        # 3. 更新缓存表（实时报价与指标）
        if not cache:
            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = data.quote.price
        cache.change_percent = data.quote.change_percent
        
        # 映射技术指标
        if data.technical and data.technical.indicators:
            ind = data.technical.indicators
            cache.rsi_14 = ind.get('rsi_14', cache.rsi_14)
            cache.ma_20 = ind.get('ma_20', cache.ma_20)
            cache.ma_50 = ind.get('ma_50', cache.ma_50)
            cache.ma_200 = ind.get('ma_200', cache.ma_200)
            cache.macd_val = ind.get('macd_val', cache.macd_val)
            cache.macd_signal = ind.get('macd_signal', cache.macd_signal)
            cache.macd_hist = ind.get('macd_hist', cache.macd_hist)
            cache.bb_upper = ind.get('bb_upper', cache.bb_upper)
            cache.bb_middle = ind.get('bb_middle', cache.bb_middle)
            cache.bb_lower = ind.get('bb_lower', cache.bb_lower)
            cache.atr_14 = ind.get('atr_14', cache.atr_14)
            cache.k_line = ind.get('k_line', cache.k_line)
            cache.d_line = ind.get('d_line', cache.d_line)
            cache.j_line = ind.get('j_line', cache.j_line)
            cache.volume_ma_20 = ind.get('volume_ma_20', cache.volume_ma_20)
            cache.volume_ratio = ind.get('volume_ratio', cache.volume_ratio)
            # 新增专业指标映射
            cache.macd_hist_slope = ind.get('macd_hist_slope', cache.macd_hist_slope)
            cache.adx_14 = ind.get('adx_14', cache.adx_14)
            cache.pivot_point = ind.get('pivot_point', cache.pivot_point)
            cache.resistance_1 = ind.get('resistance_1', cache.resistance_1)
            cache.resistance_2 = ind.get('resistance_2', cache.resistance_2)
            cache.support_1 = ind.get('support_1', cache.support_1)
            cache.support_2 = ind.get('support_2', cache.support_2)

        cache.market_status = MarketStatus.OPEN
        cache.last_updated = now

        # 4. 更新新闻（采用 upsert 逻辑）
        if data.news:
            from sqlalchemy.dialects.sqlite import insert
            for n in data.news:
                if not n.link: continue
                
                news_stmt = insert(StockNews).values(
                    id=n.id or str(hash(n.link)),
                    ticker=ticker,
                    title=n.title or "No Title",
                    publisher=n.publisher or "Unknown",
                    link=n.link,
                    summary=n.summary,
                    publish_time=n.publish_time or now
                ).on_conflict_do_nothing()
                await db.execute(news_stmt)

        await db.commit()
        try: await db.refresh(cache)
        except Exception: pass
        return cache

    @staticmethod
    async def _handle_simulation(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        """
        在网络请求不可用时，通过模拟波动的形式保证 UI 仍然有数据展示
        """
        import random
        if cache:
            fluctuation = 1 + (random.uniform(-0.0005, 0.0005))
            cache.current_price *= fluctuation
            cache.last_updated = now
            return cache
        
        return MarketDataCache(
            ticker=ticker,
            current_price=100.0 * (1 + random.uniform(-0.01, 0.01)),
            change_percent=random.uniform(-2.0, 2.0),
            rsi_14=50.0,
            ma_50=100.0,
            ma_200=100.0,
            macd_val=0.0,
            macd_hist=0.0,
            bb_upper=105.0,
            bb_lower=95.0,
            last_updated=now,
            market_status=MarketStatus.OPEN
        )
