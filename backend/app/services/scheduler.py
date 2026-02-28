import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.stock import MarketDataCache
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)

# 时区定义
CN_TZ = pytz.timezone("Asia/Shanghai")
US_TZ = pytz.timezone("America/New_York")

def should_refresh(ticker: str, last_updated: datetime) -> bool:
    """
    不仅判断当前是否开盘，还需判定在休市后，最近一次数据是否已经同步到收盘价。
    """
    now_utc = datetime.now(pytz.utc)
    ticker = ticker.upper()
    
    # 辅助函数：获取指定时区的最近一个交易日结束时间
    def get_last_session_end(tz, close_hour, close_min):
        now_local = now_utc.astimezone(tz)
        # 今天的理论收盘时间
        today_close = now_local.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)
        
        # 如果今天是周末，回退到周五
        if today_close.weekday() == 5: # Saturday
            today_close -= timedelta(days=1)
        elif today_close.weekday() == 6: # Sunday
            today_close -= timedelta(days=2)
            
        # 如果现在还没到今天的收盘时间，则“最近一次收盘”应该是前一个交易日
        if now_local < today_close:
            days_back = 1
            if today_close.weekday() == 0: # Monday -> Friday
                days_back = 3
            today_close -= timedelta(days=days_back)
            
        return today_close

    # 1. 确定市场参数
    if ticker.isdigit() and len(ticker) == 6: # A股
        tz, close_h, close_m = CN_TZ, 15, 0
        market_open = (time(9, 15) <= now_utc.astimezone(tz).time() <= time(11, 30)) or \
                      (time(13, 0) <= now_utc.astimezone(tz).time() <= time(15, 0))
    elif (ticker.isdigit() and len(ticker) == 5) or ticker.endswith(".HK"): # 港股
        tz, close_h, close_m = CN_TZ, 16, 0
        market_open = (time(9, 30) <= now_utc.astimezone(tz).time() <= time(12, 0)) or \
                      (time(13, 0) <= now_utc.astimezone(tz).time() <= time(16, 0))
    else: # 美股
        tz, close_h, close_m = US_TZ, 16, 0
        market_open = time(9, 30) <= now_utc.astimezone(tz).time() <= time(16, 0)

    # 2. 逻辑判定
    # 如果正在开盘，且数据超过 5 分钟没更新，则刷新
    if market_open:
        if last_updated.tzinfo is None:
            last_updated = pytz.utc.localize(last_updated)
        return (now_utc - last_updated) > timedelta(minutes=5)
    
    # 如果休市，检查最后更新时间是否早于最近一次收盘时间
    last_session_end = get_last_session_end(tz, close_h, close_m)
    if last_updated.tzinfo is None:
        last_updated = pytz.utc.localize(last_updated)
    
    # 如果最后一次抓取是在收盘前，则需要进行一次“盘后补录”来锁定收盘价
    return last_updated < last_session_end

async def refresh_all_stocks():
    """
    后台轮询任务：遍历数据库中所有活跃股票，并对比开盘时间及收盘补录逻辑进行更新
    """
    async with SessionLocal() as db:
        try:
            # 1. 获取所有需要关注的股票及其最后更新时间
            stmt = select(MarketDataCache)
            result = await db.execute(stmt)
            caches = result.scalars().all()
            
            if not caches:
                return

            # 2. 判定哪些股票需要刷新
            active_tickers = [c.ticker for c in caches if should_refresh(c.ticker, c.last_updated)]
            
            if not active_tickers:
                logger.debug("所有数据均已达到最新（包含盘后收盘价），跳过本轮刷新。")
                return
                
            logger.info(f"[Scheduler] 发现 {len(active_tickers)} 只股票需要更新（盘中或盘后补录），开始后台刷新...")
            
            # 3. 并发刷新 (使用信号量限制压力)
            semaphore = asyncio.Semaphore(3)
            
            async def safe_refresh(t):
                async with semaphore:
                    try:
                        # 增加微小延迟，防止瞬时撞击三方 API (Tavily/AkShare)
                        await asyncio.sleep(1)
                        # 使用独立的 session 防止冲突
                        async with SessionLocal() as local_db:
                            # 后台自动刷新强制跳过新闻抓取 (skip_news=True)，以节省终端/Tavily 额度
                            await MarketDataService.get_real_time_data(t, local_db, force_refresh=True, skip_news=True)
                        logger.info(f"[Scheduler] 成功更新股票行情: {t}")
                    except Exception as e:
                        logger.error(f"[Scheduler] 刷新 {t} 失败: {e}")

            tasks = [safe_refresh(t) for t in active_tickers]
            # 串行执行或小并发执行，确保 API 稳定性
            for task in tasks:
                await task
            
            logger.info(f"[Scheduler] 本轮后台刷新成功完成，共更新 {len(active_tickers)} 只标的。")
            
        except Exception as e:
            logger.error(f"[Scheduler] 轮询任务发生异常: {e}")

from app.services.macro_service import MacroService

# ... inside refresh_all_stocks or as a separate task ...

async def refresh_macro_radar():
    """定时更新全球宏观雷达 (每 4 小时)"""
    try:
        logger.info("[Scheduler] 开始例行更新全球宏观雷达...")
        await MacroService.update_global_radar()
        logger.info("[Scheduler] 全球宏观雷达更新完成。")
    except Exception as e:
        logger.error(f"[Scheduler] 宏观雷达更新失败: {e}")

async def refresh_cls_news():
    """定时更新财联社全球快讯 (每 10 分钟)"""
    try:
        logger.info("[Scheduler] 开始同步财联社全球快讯...")
        await MacroService.update_cls_news()
        logger.info("[Scheduler] 财联社快讯同步完成。")
    except Exception as e:
        logger.error(f"[Scheduler] 财联社快讯更新失败: {e}")

async def start_scheduler():
    """
    启动常驻后台循环
    """
    logger.info("[Scheduler] 调度中心全面启动")
    
    # 记录各任务最后执行时间
    last_macro_update = datetime.min
    last_news_update = datetime.min
    
    while True:
        # 1. 股票行情刷新 (每 5 分钟尝试一次)
        try:
            await refresh_all_stocks()
        except Exception as e:
            logger.error(f"[Scheduler] 股票行情刷新异常: {e}")

        # 2. 财联社全球快讯刷新 (每 10 分钟尝试一次)
        if datetime.now() - last_news_update > timedelta(minutes=10):
            try:
                await refresh_cls_news()
                last_news_update = datetime.now()
            except Exception as e:
                logger.error(f"[Scheduler] 财联社刷新异常: {e}")

        # 3. 宏观热点刷新 (每 4 小时尝试一次)
        if datetime.now() - last_macro_update > timedelta(hours=4):
            try:
                await refresh_macro_radar()
                last_macro_update = datetime.now()
            except Exception as e:
                logger.error(f"[Scheduler] 宏观刷新异常: {e}")
        
        await asyncio.sleep(300) 
