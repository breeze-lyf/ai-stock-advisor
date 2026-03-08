from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.security import sanitize_float
from app.models.stock import Stock, MarketDataCache, MarketStatus, StockNews
from app.services.market_providers import ProviderFactory
from app.schemas.market_data import FullMarketData, ProviderTechnical

logger = logging.getLogger(__name__)

# 市场数据分析中台 (Market Data Service Hub)
# 职责：负责从外部获取行情、技术指标、新闻，处理数据缓存，并把信息同步到数据库中。
# 这是本项目的“行情发动机”。
class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "YFINANCE", force_refresh: bool = False, price_only: bool = False, skip_news: bool = False):
        """
        核心方法：获取单支股票最新的行情。支持 price_only 模式以提高响应速度。
        """
        if ticker.lower() == "portfolio":
            return None

        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        # 如果不是强制刷新，且缓存时间在 1 分钟内，且满足数据完整度要求，则返回缓存
        #（即：要么请求仅需价格，要么缓存中已有完整指标数据）
        if not force_refresh and cache and (now - cache.last_updated) < timedelta(minutes=1):
            if price_only or cache.rsi_14 is not None:
                return cache

        # 智能判定：如果 force_refresh=True 且没有显式要求 skip_news，
        # 则检查数据库近期是否已有新闻（缓存 4 小时）
        if not skip_news and force_refresh:
            from app.models.stock import StockNews
            # 检查最近 4 小时内是否有新闻更新
            news_stmt = select(StockNews).where(StockNews.ticker == ticker).order_by(StockNews.publish_time.desc()).limit(1)
            result = await db.execute(news_stmt)
            latest_news = result.scalar_one_or_none()
            
            if latest_news and (datetime.utcnow() - latest_news.publish_time).total_seconds() < 4 * 3600:
                skip_news = True
                logger.info(f"Skipping Tavily for {ticker} as news is recently updated within 4 hours.")

        # 2. 第二步：执行真正的抓取
        data = await MarketDataService._fetch_from_providers(ticker, preferred_source, price_only=price_only, skip_news=skip_news)

        if not data:
            if cache:
                logger.warning(f"{ticker} 实时刷新失败，回退到使用现有缓存数据。")
                return cache
            
            # 只有在完全没有历史数据的情况下才进入模拟模式
            cache = await MarketDataService._handle_simulation(ticker, cache, now)
            await db.commit()
            return cache

        return await MarketDataService._update_database(ticker, data, cache, db, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str, price_only: bool = False, skip_news: bool = False) -> Optional[FullMarketData]:
        """
        底层抓取器：支持 price_only 模式跳过重型指标和新闻，支持 skip_news 排除 Tavily。
        """
        provider = ProviderFactory.get_provider(ticker, preferred_source)
        
        # 如果是极速模式，优先尝试 get_quote
        if price_only:
            try:
                quote = await provider.get_quote(ticker)
                if quote:
                    return FullMarketData(quote=quote)
            except Exception as e:
                logger.error(f"Price only fetch failed for {ticker}: {e}")
                return None

        # 非 price_only 模式或全能接口尝试
        result = await provider.get_full_data(ticker)
        if result:
            return result

        try:
            quote_task = asyncio.create_task(provider.get_quote(ticker))
            
            # 如果 price_only 为 True，则不创建以下重型任务
            fundamental_task = None
            indicator_task = None
            news_tasks = []

            if not price_only:
                fundamental_task = asyncio.create_task(provider.get_fundamental_data(ticker))
                indicator_task = asyncio.create_task(provider.get_historical_data(ticker, period="200d"))
                
                from app.services.market_providers.tavily import TavilyProvider
                tavily = TavilyProvider()
                
                # 原始新闻源（AkShare/Tencent）总是开启（不计费）
                news_tasks = [asyncio.create_task(provider.get_news(ticker))]
                
                # Tavily 仅在不 skip_news 时开启
                if not skip_news and tavily.api_key:
                    news_tasks.append(asyncio.create_task(tavily.get_news(ticker)))
                
                is_us = not (ticker.isdigit() and len(ticker) == 6)
                if is_us and type(provider).__name__ == "AkShareProvider":
                    try:
                        from app.services.market_providers.yfinance import YFinanceProvider
                        yf_p = YFinanceProvider()
                        news_tasks.append(asyncio.create_task(yf_p.get_news(ticker)))
                    except Exception as e:
                        logger.warning(f"Failed to load YFinanceProvider for news: {e}")

            # 核心任务列表，过滤掉 None
            core_tasks = [quote_task]
            if indicator_task: core_tasks.append(indicator_task)
            
            core_gather = asyncio.gather(*core_tasks, return_exceptions=True)
            try:
                core_res = await asyncio.wait_for(core_gather, timeout=15.0)
                if len(core_tasks) == 2:
                    quote, indicators = core_res
                else:
                    quote, indicators = core_res[0], None
            except asyncio.TimeoutError:
                logger.warning(f"{ticker} 核心报价/指标抓取超时 (15s)")
                quote, indicators = None, None
            except Exception as e:
                logger.error(f"{ticker} 核心抓取异常: {e}")
                quote, indicators = None, None

            # 基本面数据获取 (增强版：包含百分位与资金流)
            # 逻辑修复：即使 fundamental_task 失败，只要 val_data 或 flow_data 有数据，也应返回
            fundamental = None
            if fundamental_task:
                try:
                    # 并行获取基础面、估值百分位、资金流
                    valuation_task = asyncio.create_task(provider.get_valuation_percentiles(ticker))
                    flow_task = asyncio.create_task(provider.get_capital_flow(ticker))
                    
                    f_res, val_data, flow_data = await asyncio.gather(
                        fundamental_task, valuation_task, flow_task, return_exceptions=True
                    )
                    
                    # 即使核心 fundamental 抓取异常或为空，我们也创建一个容器来存放百分位和资金流
                    if isinstance(f_res, Exception) or not f_res:
                        fundamental = ProviderFundamental()
                        logger.info(f"{ticker} main fundamental task failed, creating empty container for quant metrics")
                    else:
                        fundamental = f_res
                    
                    # 注入百分位数据
                    if not isinstance(val_data, Exception) and val_data:
                        fundamental.pe_percentile = val_data.get("pe_percentile")
                        fundamental.pb_percentile = val_data.get("pb_percentile")
                    
                    # 注入资金流数据
                    if not isinstance(flow_data, Exception) and flow_data:
                        fundamental.net_inflow = flow_data.get("net_inflow")
                        
                    # 如果最后还是全空，则设为 None
                    if all(getattr(fundamental, f) is None for f in fundamental.model_fields):
                        fundamental = None

                except Exception as e:
                    logger.error(f"{ticker} 增强基本面异常: {e}")
                    fundamental = None

            # 新闻数据并行获取，极短超时 (最高 1.5 秒) 防止拖累响应
            news = []
            if news_tasks:
                news_gather = asyncio.gather(*news_tasks, return_exceptions=True)
                try:
                    # 扣除核心任务已耗费的时间，最多再等 2.0 秒
                    news_res = await asyncio.wait_for(news_gather, timeout=2.0) # Bumped timeout to 2s
                    # 合并并去重
                    seen_links = set()
                    for nr in news_res:
                        if isinstance(nr, list):
                            for item in nr:
                                if item.link and item.link not in seen_links:
                                    news.append(item)
                                    seen_links.add(item.link)
                        elif isinstance(nr, Exception) and "432" in str(nr): # Tavily 432 error handling
                            logger.warning(f"Tavily news for {ticker} returned 432 error, likely rate limit or invalid query. Skipping.")
                        elif isinstance(nr, Exception):
                            logger.warning(f"News task for {ticker} failed with: {nr}")
                    
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
                except Exception as e:
                    logger.warning(f"{ticker} 新闻处理异常: {e}")
            
            # 将结果组装成统一的 FullMarketData 结构体
            if quote and not isinstance(quote, Exception):
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators) if not isinstance(indicators, Exception) and indicators else None,
                    news=news
                )
        except Exception as e:
            logger.error(f"从 {type(provider).__name__} 获取 {ticker} 数据时发生错误: {e}")

        # 故障转移：如果用户选的源失败了，且是美股，强制用 YFinance 尝试最后一遍
        # 排除 A 股 (6位数字)，因为 YFinance 在国内访问非常慢且数据对 A 股不准
        is_us = not (ticker.isdigit() and len(ticker) == 6)
        if preferred_source != "YFINANCE" and is_us:
            yf_provider = ProviderFactory.get_provider(ticker, "YFINANCE")
            return await yf_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        """
        数据库持久化：把网络抓取来的“散乱数据”精准地填入数据库表里。
        """
        # 1. 处理 Stock 基础表 (使用插入/更新原子操作)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        stock_values = {
            "ticker": ticker,
            "name": data.quote.name or ticker
        }
        
        # 预先处理基本面字段（如果有数据）
        fundamental = data.fundamental
        if fundamental:
            logger.info(f"Syncing fundamental for {ticker}: market_cap={fundamental.market_cap}, PE={fundamental.pe_ratio}")
            fields = ['sector', 'industry', 'market_cap', 'pe_ratio', 'forward_pe', 'eps', 'dividend_yield', 'beta', 'fifty_two_week_high', 'fifty_two_week_low']
            for field in fields:
                val = getattr(fundamental, field, None)
                if val is not None:
                    stock_values[field] = val

        # 执行 Stock 表的原子操作
        stock_upsert = pg_insert(Stock).values(stock_values)
        # 如果冲突，更新名称和基本面字段
        update_cols = {k: v for k, v in stock_values.items() if k != "ticker"}
        # 特殊逻辑：仅当新名称不是 ticker 时才更新名称
        if stock_values["name"] == ticker:
            update_cols.pop("name", None)
            
        stock_upsert = stock_upsert.on_conflict_do_update(
            index_elements=["ticker"],
            set_=update_cols
        )
        await db.execute(stock_upsert)

        # 2. 处理 MarketDataCache (使用插入/更新原子操作)
        cache_values = {
            "ticker": ticker,
            "current_price": sanitize_float(data.quote.price, 0.0),
            "change_percent": sanitize_float(data.quote.change_percent, 0.0),
            "market_status": data.quote.market_status or MarketStatus.OPEN.value,
            "last_updated": now
        }
        
        # 注入基本面推导的量化字段
        if fundamental:
            cache_values["pe_percentile"] = sanitize_float(fundamental.pe_percentile)
            cache_values["pb_percentile"] = sanitize_float(fundamental.pb_percentile)
            cache_values["net_inflow"] = sanitize_float(fundamental.net_inflow)

        # 注入技术指标
        if data.technical and data.technical.indicators:
            ind = data.technical.indicators
            tech_fields = [
                'rsi_14', 'ma_20', 'ma_50', 'ma_200', 'macd_val', 'macd_signal', 
                'macd_hist', 'bb_upper', 'bb_middle', 'bb_lower', 'atr_14', 
                'k_line', 'd_line', 'j_line', 'volume_ma_20', 'volume_ratio', 
                'macd_hist_slope', 'macd_cross', 'macd_is_new_cross', 'adx_14', 'pivot_point'
            ]
            for f in tech_fields:
                if f in ind:
                    cache_values[f] = ind[f]
            
            # 盈亏比计算 (逻辑同前，但在 atomic 操作前计算)
            # 注意：此处使用 data.quote.price (现价) 和 支撑/阻力位进行重算
            res = cache_values.get('resistance_1') or (cache.resistance_1 if cache else None) or ind.get('resistance_1')
            sup = cache_values.get('support_1') or (cache.support_1 if cache else None) or ind.get('support_1')
            curr_p = cache_values["current_price"]

            if res and sup and curr_p:
                reward = sanitize_float(res) - sanitize_float(curr_p)
                risk = sanitize_float(curr_p) - sanitize_float(sup)
                
                # 如果不是 AI 锁定的，更新支撑阻力
                is_ai = cache.is_ai_strategy if cache else False
                if not is_ai:
                    cache_values['resistance_1'] = sanitize_float(ind.get('resistance_1'))
                    cache_values['resistance_2'] = sanitize_float(ind.get('resistance_2'))
                    cache_values['support_1'] = sanitize_float(ind.get('support_1'))
                    cache_values['support_2'] = sanitize_float(ind.get('support_2'))

                if risk and risk > 0.01:
                    cache_values['risk_reward_ratio'] = round(reward / risk, 2) if reward > 0 else 0.0

        # 执行 Cache 表的原子操作
        cache_upsert = pg_insert(MarketDataCache).values(cache_values)
        update_set = {k: v for k, v in cache_values.items() if k != "ticker"}
        
        # 如果是 AI 策略锁定，不要覆盖支撑阻力位
        if cache and cache.is_ai_strategy:
            for k in ['resistance_1', 'resistance_2', 'support_1', 'support_2', 'risk_reward_ratio']:
                update_set.pop(k, None)
                
        cache_upsert = cache_upsert.on_conflict_do_update(
            index_elements=["ticker"],
            set_=update_set
        )
        await db.execute(cache_upsert)

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
                # 批量插入新闻以解决远程数据库的插入延迟
                news_stmt = insert(StockNews).values(news_values).on_conflict_do_nothing()
                await db.execute(news_stmt)

        await db.commit()
        
        # 重新获取最新的对象以返回，因为 UPSERT 是绕过 ORM 追踪的原生 SQL
        try: 
            stock_stmt = select(Stock).where(Stock.ticker == ticker)
            stock_res = await db.execute(stock_stmt)
            stock = stock_res.scalar_one_or_none()
            
            cache_stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
            cache_res = await db.execute(cache_stmt)
            cache = cache_res.scalar_one_or_none()

            if stock: await db.refresh(stock)
            if cache: await db.refresh(cache)
        except Exception as e: 
            logger.error(f"Error during db re-fetching/refresh: {e}")
            
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
