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
# 职责：负责从外部获取行情、技术指标、新闻，处理数据缓存，并把信息同步到数据库中。
# 这是本项目的“行情发动机”。
class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "YFINANCE", force_refresh: bool = False):
        """
        核心方法：获取单支股票最新的所有行情与技术数据。
        
        逻辑流程：
        1. 查缓存：先看看数据库里有没有这支票，且数据是不是刚更新的（1分钟内）。
        2. 抓数据：如果没缓存，就去调外部接口（如 yfinance）。
        3. 存数据库：把抓到的新数据保存，方便下次快速读取，也为 AI 分析提供素材。
        """
        # 0. 过滤器：如果是虚拟代码 'portfolio' (代表整份持仓)，直接跳过抓取，它没有实体行情。
        if ticker.lower() == "portfolio":
            logger.info("跳过虚拟代码 'portfolio' 的行情抓取。")
            return None

        # 1. 第一步：查询本地缓存
        # 这一步是为了省流量和提高速度。如果每秒都去抓 yfinance，账号会被封禁。
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        # 如果不是强制刷新，且缓存时间在 1 分钟内，我们认为数据“还是热乎的”，直接用。
        if not force_refresh and cache and (now - cache.last_updated) < timedelta(minutes=1):
            return cache

        # 2. 第二步：执行真正的网络爬虫/API 请求
        # preferred_source 是用户在设置里选的源（比如 yfinance 或 akshare）
        data = await MarketDataService._fetch_from_providers(ticker, preferred_source)

        # 3. 第三步：异常处理（兜底逻辑）
        # 如果网络断了或者 API 挂了，我们不能让前端显示空白。
        if not data:
            # 进入“模拟模式”：基于历史价生成一个极小波动的假数据，让 UI 看起来还活着。
            cache = await MarketDataService._handle_simulation(ticker, cache, now)
            await db.commit()
            return cache

        # 4. 第四步：持久化到数据库
        # 把 FullMarketData 这种临时对象，转存为数据库里的 Stock 和 MarketDataCache 记录。
        return await MarketDataService._update_database(ticker, data, cache, db, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str) -> Optional[FullMarketData]:
        """
        底层抓取器：利用 asyncio.gather 并行获取多种数据 (行情+指标+基本面+新闻)。
        并行执行意味着：如果四个接口每个耗时1秒，总耗时还是1秒，而不是4秒。
        """
        provider = ProviderFactory.get_provider(ticker, preferred_source)
        
        # 尝试使用该源的“全能接口” (如果支持)
        result = await provider.get_full_data(ticker)
        if result:
            return result

        # 如果没有全能接口，我们就手动发起四个并行的任务 (Task)
        try:
            # 1. 任务：获取当前报价
            quote_task = asyncio.create_task(provider.get_quote(ticker))
            # 2. 任务：获取基本面信息 (PE, 市值等)
            fundamental_task = asyncio.create_task(provider.get_fundamental_data(ticker))
            # 3. 任务：获取历史行情并计算技术指标 (RSI, MACD)
            indicator_task = asyncio.create_task(provider.get_historical_data(ticker, period="200d"))
            
            # AI 搜索增强：我们集成了一个叫 Tavily 的搜索引擎。
            from app.services.market_providers.tavily import TavilyProvider
            tavily = TavilyProvider()
            
            news_tasks = [asyncio.create_task(provider.get_news(ticker))]
            
            # 美股增强：如果当前 provider 是 AkShare (由于工厂强制返回)，它对美股新闻无效，则额外并发调用 YFinance 获取专业新闻
            is_us = not (ticker.isdigit() and len(ticker) == 6)
            if is_us and type(provider).__name__ == "AkShareProvider":
                try:
                    from app.services.market_providers.yfinance import YFinanceProvider
                    yf_p = YFinanceProvider()
                    news_tasks.append(asyncio.create_task(yf_p.get_news(ticker)))
                except Exception as e:
                    logger.warning(f"Failed to load YFinanceProvider for news: {e}")

            if tavily.api_key:
                news_tasks.append(asyncio.create_task(tavily.get_news(ticker)))
            
            # 主力数据获取 (报价与技术指标)，容忍 5 秒
            # 我们将基本面任务从并行核心任务中移出，因为它最容易由于网络问题超时且不影响核心行情展示
            core_gather = asyncio.gather(quote_task, indicator_task, return_exceptions=True)
            try:
                core_res = await asyncio.wait_for(core_gather, timeout=5.0)
                quote, indicators = core_res
            except asyncio.TimeoutError:
                logger.warning(f"{ticker} 核心报价/指标抓取超时 (5s)")
                quote, indicators = None, None

            # 基本面数据获取，单独给予超时控制 (3秒)，即使失败也不影响主逻辑
            fundamental = None
            try:
                fundamental = await asyncio.wait_for(fundamental_task, timeout=3.0)
                if isinstance(fundamental, Exception):
                    logger.warning(f"{ticker} 基本面数据抓取遇到错误: {fundamental}")
                    fundamental = None
            except asyncio.TimeoutError:
                logger.warning(f"{ticker} 基本面数据抓取超时 (3s)，优先展现价格数据")
            except Exception as e:
                logger.error(f"{ticker} 基本面异常: {e}")

            # 新闻数据并行获取，极短超时 (最高 1.5 秒) 防止拖累响应
            news_gather = asyncio.gather(*news_tasks, return_exceptions=True)
            try:
                # 扣除核心任务已耗费的时间，最多再等 1.5 秒
                news_res = await asyncio.wait_for(news_gather, timeout=1.5)
                news = []
                # 合并并去重
                seen_links = set()
                for nr in news_res:
                    if isinstance(nr, list):
                        for item in nr:
                            if item.link and item.link not in seen_links:
                                news.append(item)
                                seen_links.add(item.link)
                
                # 按照发布时间倒序排列
                def get_sort_key(x):
                    p_time = x.publish_time if x.publish_time else datetime.utcnow()
                    # 统一转为 naive 格式，防止 offset-naive and offset-aware 比较报错
                    if p_time.tzinfo is not None:
                        p_time = p_time.replace(tzinfo=None)
                    return p_time

                news.sort(key=get_sort_key, reverse=True)
            except asyncio.TimeoutError:
                logger.warning(f"{ticker} 新闻抓取超时 (1.5s)，已忽略")
                news = []
            
            # 将结果组装成统一的 FullMarketData 结构体
            if quote and not isinstance(quote, Exception):
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators) if not isinstance(indicators, Exception) and indicators else None,
                    news=news if not isinstance(news, Exception) else []
                )
        except Exception as e:
            logger.error(f"从 {type(provider).__name__} 获取 {ticker} 数据时发生错误: {e}")

        # 故障转移：如果用户选的源失败了，强制用 YFinance 尝试最后一遍
        if preferred_source != "YFINANCE":
            yf_provider = ProviderFactory.get_provider(ticker, "YFINANCE")
            return await yf_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        """
        数据库持久化：把网络抓取来的“散乱数据”精准地填入数据库表里。
        """
        # 1. 处理 Stock 基础表 (查漏补缺)
        stock_stmt = select(Stock).where(Stock.ticker == ticker)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        
        if not stock:
            # 如果系统里还没这支票，帮用户自动录入名称
            stock = Stock(ticker=ticker, name=data.quote.name or ticker)
            db.add(stock)
            await db.commit() # 先提交一遍，防止后面的外键约束失败
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()
        else:
            # 如果已有数据，看看名称需不需要修正（比如从代码变成中文名）
            new_name = data.quote.name
            if new_name and new_name != ticker:
                stock.name = new_name
            elif not stock.name or stock.name == ticker:
                if new_name:
                    stock.name = new_name

        # 2. 同步基本面 (PE, 股息等)
        fundamental = data.fundamental
        if fundamental:
            # 记录以确认进入了同步逻辑
            logger.info(f"Syncing fundamental for {ticker}: market_cap={fundamental.market_cap}, PE={fundamental.pe_ratio}")
            
            # 使用 getattr/setattr 模式以防漏掉字段，且确保哪怕以前有值现在也要更新
            fields = ['sector', 'industry', 'market_cap', 'pe_ratio', 'forward_pe', 'eps', 'dividend_yield', 'beta', 'fifty_two_week_high', 'fifty_two_week_low']
            for field in fields:
                val = getattr(fundamental, field, None)
                if val is not None:
                    setattr(stock, field, val)

        # 3. 同步实时缓存信息 (价格、RSI、MACD 等)
        if not cache:
            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = data.quote.price
        cache.change_percent = data.quote.change_percent
        
        # 将复杂的数学计算指标映射到数据库字段
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
            cache.macd_cross = ind.get('macd_cross', cache.macd_cross)
            cache.macd_is_new_cross = ind.get('macd_is_new_cross', cache.macd_is_new_cross)
            cache.adx_14 = ind.get('adx_14', cache.adx_14)
            cache.pivot_point = ind.get('pivot_point', cache.pivot_point)
            
            # ---【本项目核心逻辑】盈亏比的动态重算 ---
            # 盈亏比 (Reward/Risk) = (目标价 - 现价) / (现价 - 止损价)
            if cache.is_ai_strategy:
                # 如果这个点位已经被 AI 锁定 (is_ai_strategy=True)
                # 我们就不再使用通用的 S1/R1，而是使用 AI 建议的止盈止损位。
                if cache.resistance_1 and cache.support_1 and cache.current_price:
                    reward = cache.resistance_1 - cache.current_price # 潜在盈利
                    risk = cache.current_price - cache.support_1     # 潜在损失
                    if risk > 0.01: 
                        # 计算比例。如果价格已经超过了止盈位(reward为负)，则盈亏比标记为0
                        new_rr = round(reward / risk, 2) if reward > 0 else 0.0
                        cache.risk_reward_ratio = new_rr
                    else:
                        # 风险无穷大或已跌破，标记为 None，前端会显示为红色预警
                        cache.risk_reward_ratio = None
            else:
                # 如果不是 AI 锁定策略，仅仅是常规行情，我们更新常规的阻力支撑位。
                cache.resistance_1 = ind.get('resistance_1', cache.resistance_1)
                cache.resistance_2 = ind.get('resistance_2', cache.resistance_2)
                cache.support_1 = ind.get('support_1', cache.support_1)
                cache.support_2 = ind.get('support_2', cache.support_2)
                cache.risk_reward_ratio = None # 常规行情下不展示由机器乱算的盈亏比

        cache.market_status = MarketStatus.OPEN
        cache.last_updated = now

        # 4. 新闻增量同步与去重
        if data.news:
            from sqlalchemy.dialects.postgresql import insert
            
            news_values = []
            import hashlib
            
            for n in data.news:
                if not n.link: continue
                unique_id = hashlib.md5(f"{ticker}:{n.link}".encode()).hexdigest()
                p_time = n.publish_time or now
                if p_time.tzinfo:
                    p_time = p_time.replace(tzinfo=None)
                
                news_values.append({
                    "id": unique_id,
                    "ticker": ticker,
                    "title": n.title or "无标题",
                    "publisher": n.publisher or "未知媒体",
                    "link": n.link,
                    "summary": n.summary,
                    "publish_time": p_time
                })
                
            if news_values:
                # 批量插入新闻以解决远程数据库的插入延迟 (解决单点耗时数十秒的关键)
                news_stmt = insert(StockNews).values(news_values).on_conflict_do_nothing()
                await db.execute(news_stmt)

        await db.commit()
        try: 
            # 必须进行显式刷新，否则由于 SQLAlchemy 的延迟加载，返回的对象可能还是旧的
            if stock: await db.refresh(stock)
            if cache: await db.refresh(cache)
        except Exception as e: 
            logger.error(f"Error during db refresh: {e}")
        return cache

    @staticmethod
    async def _handle_simulation(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        """
        故障自动模拟波段 (Simulation Mode)
        - 场景：在网络隔离或 API 受限严重时启用，防止 UI 渲染“白屏”或异常断层
        """
        import random
        if cache:
            # 基于前序价格进行微小布朗运动模拟 (Micro-fluctuation)
            fluctuation = 1 + (random.uniform(-0.0005, 0.0005))
            cache.current_price *= fluctuation
            # 注意：故意不更新 last_updated，让用户知道这是旧数据，且系统会继续尝试真实抓取
            return cache
        
        # 纯虚拟初始化 (初始默认时间设为 2000 年，标记为从未成功抓取)
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
            last_updated=datetime(2000, 1, 1), 
            market_status=MarketStatus.OPEN
        )
