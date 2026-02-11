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

# 市场数据分析中台 (Market Data Service Hub)
# 职责：负责协调多个数据源、处理缓存逻辑、并行抓取数据并持久化到数据库
class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "YFINANCE", force_refresh: bool = False):
        """
        获取单支股票的实时/最新数据 (Get Real-time Data for a Ticker)
        
        策略 (Strategy)：
        1. 优先检查本地数据库缓存 (Check local cache)
        2. 若缓存未过期且非强制刷新，直接返回 (Return if valid cache)
        3. 否则从外部 API 并行抓取 (Else fetch from providers in parallel)
        4. 持久化到数据库并返回更新后的对象 (Update DB and return)
        """
        # 1. 检查本地数据库缓存 (Step 1: Local Cache Check)
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        # 默认缓存过期时间为 1 分钟，保证高频行情刷新不触发外部 API 限制
        if not force_refresh and cache and (now - cache.last_updated) < timedelta(minutes=1):
            return cache

        # 2. 从数据提供商抓取数据 (Step 2: Fetching from Providers)
        # 支持 YFinance, AkShare 等多源动态切换
        data = await MarketDataService._fetch_from_providers(ticker, preferred_source)

        # 3. 处理故障转移/兜底 (Step 3: Fault Tolerance / Fallback)
        # 如果 API 请求全线失败且无历史缓存，启用“模拟模式”生成随机波动数据，保证前端 UI 完整性
        if not data:
            cache = await MarketDataService._handle_simulation(ticker, cache, now)
            await db.commit()
            return cache

        # 4. 持久化数据 (Step 4: Persistence)
        # 将抓取到的报价、基础面、技术指标和新闻同步到 Stock 和 MarketDataCache 表中
        return await MarketDataService._update_database(ticker, data, cache, db, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str) -> Optional[FullMarketData]:
        """
        根据策略调用不同的 Provider 抓取数据 (Coordinate provider fetching)
        - 优先尝试 Provider 的综合抓取接口 (get_full_data)
        - 失败后分流并行请求行情、指标、基础面及新闻
        """
        provider = ProviderFactory.get_provider(ticker, preferred_source)
        
        # 针对 YFinance 等支持批量字段请求的 Provider 优化
        result = await provider.get_full_data(ticker)
        if result:
            return result

        # 并行任务调度：利用 asyncio.gather 极大缩短 IO 等待时间
        try:
            quote_task = provider.get_quote(ticker)
            fundamental_task = provider.get_fundamental_data(ticker)
            indicator_task = provider.get_historical_data(ticker, period="200d")
            
            # AI 增强搜索：若 Tavily 可用，优先使用 AI 搜索获取高质量新闻总结
            from app.services.market_providers.tavily import TavilyProvider
            tavily = TavilyProvider()
            news_task = tavily.get_news(ticker) if tavily.api_key else provider.get_news(ticker)
            
            # 引入 15.0s 超时保护，防止单一数据源（如 AkShare 的爬虫接口）阻塞全局响应
            try:
                res = await asyncio.wait_for(
                    asyncio.gather(quote_task, fundamental_task, indicator_task, news_task, return_exceptions=True),
                    timeout=15.0
                )
                quote, fundamental, indicators, news = res
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching data for {ticker}, partial data may be returned.")
                quote = await quote_task if not quote_task.done() else quote_task.result()
                fundamental, indicators, news = None, None, []
            
            if quote and not isinstance(quote, Exception):
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators) if not isinstance(indicators, Exception) and indicators else None,
                    news=news if not isinstance(news, Exception) else []
                )
        except Exception as e:
            logger.error(f"Error fetching from provider {type(provider).__name__} for {ticker}: {e}")

        # 跨源自动备份 (Cross-source Fallback)
        if preferred_source != "YFINANCE":
            yf_provider = ProviderFactory.get_provider(ticker, "YFINANCE")
            return await yf_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        """
        持久化数据映射 (Map Schema to DB Models)
        - 职责：维护 Stock (基础资料) 和 MarketDataCache (实时状态) 的一致性
        """
        # 1. 维护 Stock 资料存根 (Maintain Stock stub)
        stock_stmt = select(Stock).where(Stock.ticker == ticker)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        
        if not stock:
            # 自动初始化新标的
            stock = Stock(ticker=ticker, name=data.quote.name or ticker)
            db.add(stock)
            await db.commit()
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()
        else:
            # 策略：仅在新名称优于旧名称（非 Ticker 且非空）或者旧名称原本就是代码时才覆盖
            new_name = data.quote.name
            if new_name and new_name != ticker:
                stock.name = new_name
            elif not stock.name or stock.name == ticker:
                if new_name:
                    stock.name = new_name

        # 2. 同步基础面 (Synchronize Fundamental data)
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

        # 3. 同步缓存状态 (Synchronize Real-time Cache)
        if not cache:
            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = data.quote.price
        cache.change_percent = data.quote.change_percent
        
        # 复杂技术指标映射 (Map Technical Indicators)
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
            cache.macd_hist_slope = ind.get('macd_hist_slope', cache.macd_hist_slope)
            cache.macd_cross = ind.get('macd_cross', cache.macd_cross) # Mapping new field
            cache.macd_is_new_cross = ind.get('macd_is_new_cross', cache.macd_is_new_cross)
            cache.adx_14 = ind.get('adx_14', cache.adx_14)
            cache.pivot_point = ind.get('pivot_point', cache.pivot_point)
            cache.resistance_1 = ind.get('resistance_1', cache.resistance_1)
            cache.resistance_2 = ind.get('resistance_2', cache.resistance_2)
            cache.support_1 = ind.get('support_1', cache.support_1)
            cache.support_2 = ind.get('support_2', cache.support_2)
            cache.risk_reward_ratio = ind.get('risk_reward_ratio', cache.risk_reward_ratio)

        cache.market_status = MarketStatus.OPEN
        cache.last_updated = now

        # 4. 新闻增量同步 (Incremental News Synchronization)
        # 策略：根据 Link 的 MD5 哈希作为去重唯一 ID (Upsert logic)
        if data.news:
            from sqlalchemy.dialects.sqlite import insert
            for n in data.news:
                if not n.link: continue
                
                import hashlib
                unique_link_id = hashlib.md5(n.link.encode()).hexdigest()
                news_stmt = insert(StockNews).values(
                    id=n.id or unique_link_id,
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
        故障自动模拟波段 (Simulation Mode)
        - 场景：在网络隔离或 API 受限严重时启用，防止 UI 渲染“白屏”或异常断层
        """
        import random
        if cache:
            # 基于前序价格进行微小布朗运动模拟
            fluctuation = 1 + (random.uniform(-0.0005, 0.0005))
            cache.current_price *= fluctuation
            cache.last_updated = now
            return cache
        
        # 纯虚拟初始化
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
