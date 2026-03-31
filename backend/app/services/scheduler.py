import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from app.core.database import SessionLocal
from app.core.config import settings
from app.services.scheduler_jobs import (
    run_daily_portfolio_report_job,
    run_post_market_analysis_job,
    run_refresh_all_stocks_job,
    run_refresh_simulated_trades_job,
    run_auto_refresh_stale_analysis_job,
)

from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

async def purge_old_analysis_reports():
    """删除超过 DATA_RETENTION_DAYS 天的分析报告，控制数据库体积。"""
    cutoff = datetime.utcnow() - timedelta(days=settings.DATA_RETENTION_DAYS)
    from sqlalchemy import delete
    from app.models.analysis import AnalysisReport, PortfolioAnalysisReport
    async with SessionLocal() as db:
        try:
            r1 = await db.execute(
                delete(AnalysisReport).where(AnalysisReport.created_at < cutoff)
            )
            r2 = await db.execute(
                delete(PortfolioAnalysisReport).where(PortfolioAnalysisReport.created_at < cutoff)
            )
            await db.commit()
            total = r1.rowcount + r2.rowcount
            if total:
                logger.info(f"[Scheduler] 数据保留清理：已删除 {total} 条过期分析报告（{settings.DATA_RETENTION_DAYS}天以上）")
        except Exception as e:
            logger.error(f"[Scheduler] 数据保留清理失败: {e}")
            await db.rollback()


async def refresh_simulated_trades():
    """
    检查所有状态为 OPEN 的模拟盘交易 (SimulatedTrade) 
    1. 根据最新的 MarketDataCache 更新当前的浮动盈亏
    2. 如果触碰 target_price 或 stop_loss_price，则强制平仓
    3. 写入当天的 TradeHistoryLog (可以加上去重逻辑以确保每天只写一条)
    """
    async with SessionLocal() as db:
        try:
            updated_count, closed_count = await run_refresh_simulated_trades_job(db)
            if updated_count > 0:
                logger.info(f"[Scheduler] 完成了 {updated_count} 笔虚拟订单盯盘。其中 {closed_count} 笔触点平仓。")
        except Exception as e:
            logger.error(f"[Scheduler] 虚拟盯盘服务异常: {e}")



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
            await run_refresh_all_stocks_job(db, should_refresh, SessionLocal)
        except Exception as e:
            logger.error(f"[Scheduler] 轮询任务发生异常: {e}")

from app.services.macro_service import MacroService

# ... inside refresh_all_stocks or as a separate task ...

async def refresh_macro_radar():
    """定时更新全球宏观雷达 (每 1 小时)"""
    try:
        logger.info("[Cron] 开始例行更新全球宏观雷达...")
        await MacroService.update_global_radar()
        logger.info("[Cron] 全球宏观雷达更新完成。")
    except Exception as e:
        logger.error(f"[Cron] 宏观雷达更新失败: {e}")

async def refresh_cls_headlines():
    """定时抓取财联社深度头条 (每 4 小时)"""
    try:
        logger.info("[Scheduler] 开始探测财联社深度头条...")
        await MacroService.update_cls_headlines()
        logger.info("[Scheduler] 财联社头条更新完成。")
    except Exception as e:
        logger.error(f"[Scheduler] 财联社头条抓取失败: {e}")

async def refresh_cls_news():
    """定时更新财联社全球快讯 (每 10 分钟)"""
    try:
        logger.info("[Scheduler] 开始同步财联社全球快讯...")
        await MacroService.update_cls_news()
        logger.info("[Scheduler] 财联社快讯同步完成。")
    except Exception as e:
        logger.error(f"[Scheduler] 财联社快讯更新失败: {e}")

async def refresh_hourly_summary():
    """生成并推送每小时新闻精要摘要"""
    try:
        logger.info("[Scheduler] 正在为活跃用户生成每小时新闻精要...")
        async with SessionLocal() as db:
            repo = SchedulerRepository(db)
            active_users = await repo.get_active_hourly_summary_users()
            
            # 1. 先生成本小时全局共性分析报告 (单次 AI 调用，后续用户共享)
            await MacroService.generate_global_hourly_report(db)

            for user in active_users:
                # 熔断：如果没有配置飞书 Webhook，跳过该用户的 AI 分析任务
                if not user.feishu_webhook_url or not user.enable_hourly_summary:
                    continue

                summary_data = await MacroService.generate_hourly_news_summary(db, user.id)
                if summary_data.get("summary"):
                    await NotificationService.send_hourly_summary(
                        summary_text=summary_data["summary"],
                        count=summary_data["count"],
                        sentiment=summary_data.get("sentiment", "中性"),
                        email=user.email,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url
                    )
        logger.info(f"[Scheduler] 已完成 {len(active_users)} 位用户的摘要生成与推送。")
    except Exception as e:
        logger.error(f"[Scheduler] 每小时新闻精要生成失败: {e}")

async def refresh_post_market_analysis():
    """
    盘后 AI 深度复盘：
    1. 动态识别已收盘的市场 (A/港/美)
    2. 对当前持有该市场标的的活跃用户，触发一次完整 AI 分析
    3. 对比历史建议，如果发生重大偏差，推送 Feishu Alert
    """
    try:
        async with SessionLocal() as db:
            markets_to_process = await run_post_market_analysis_job(db)

        if not markets_to_process:
            return
        logger.info(f"[Scheduler] 盘后复盘任务处理完成: {markets_to_process}")
    except Exception as e:
        logger.error(f"[Scheduler] 盘后复盘任务失败: {e}")

async def send_daily_portfolio_report():
    """生成并发送每日持仓健康报告 (Feishu Card)"""
    try:
        async with SessionLocal() as db:
            users_count = await run_daily_portfolio_report_job(db)
            logger.info(f"[Scheduler] 已完成 {users_count} 位用户的持仓报告推送。")
    except Exception as e:
        logger.error(f"[Scheduler] 每天报告生成失败: {e}")

async def _run_auto_analysis_bg_task(session_factory):
    """auto_refresh_stale_analysis_job 的后台包装器，捕获所有异常防止 create_task 静默失败"""
    try:
        count = await run_auto_refresh_stale_analysis_job(session_factory)
        if count:
            logger.info(f"[AutoRefresh] 本轮完成 {count} 个标的的自动分析刷新")
    except Exception as e:
        logger.error(f"[AutoRefresh] 后台分析刷新任务异常: {e}")


async def start_scheduler():
    """
    启动常驻后台循环。
    分布式锁：若 Redis 可用，同一时间只有一个实例真正执行任务（适用于多 worker 部署）。
    若无 Redis，则单实例完整运行（开发环境）。
    """
    logger.info("[Scheduler] 调度中心全面启动，轮询精度：60s")
    
    # 记录各任务最后执行时间
    last_news_update = datetime.now() - timedelta(minutes=5)
    last_headline_update = datetime.now() - timedelta(hours=3)
    last_triggered_summary_hour = -1 # 记录上一次成功触发推送到小时，防止分钟内重复执行
    last_daily_report_day = ""
    last_auto_analysis_refresh = datetime.now() - timedelta(minutes=30)  # 启动即检查一次
    
    while True:
        # Distributed lock: only one instance runs per cycle when Redis is available.
        from app.core.redis_client import acquire_lock, release_lock
        lock_key = "scheduler:cycle_lock"
        if not await acquire_lock(lock_key, ttl=55):  # 55s < 60s sleep to prevent overlap
            logger.debug("[Scheduler] Another instance holds the cycle lock, skipping cycle.")
            await asyncio.sleep(60)
            continue

        try:
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

            # 2.5 每小时综合推送 (整点对齐：宏观雷达 + 新闻精要)
            now = datetime.now()
            # 拓宽触发窗口至 15 分钟，防止被行情刷新阻塞
            if now.minute < 15 and now.hour != last_triggered_summary_hour:
                try:
                    logger.info(f"[Scheduler] 🔔 检测到整点窗口 ({now.strftime('%H:%M')})，执行每小时推送任务...")
                    # A. 全球宏观雷达
                    await refresh_macro_radar()
                    # B. 每小时新闻精要
                    await refresh_hourly_summary()
                    last_triggered_summary_hour = now.hour
                    logger.info(f"[Scheduler] 整点推送任务已全部完成 (Hour: {now.hour})")
                except Exception as e:
                    logger.error(f"[Scheduler] 整点推送触发异常: {e}")

            # 3. 财联社深度头条 (每 4 小时一次)
            if datetime.now() - last_headline_update > timedelta(hours=4):
                try:
                    await refresh_cls_headlines()
                    last_headline_update = datetime.now()
                except Exception as e:
                    logger.error(f"[Scheduler] 深度头条刷新异常: {e}")

            # 4. 每日报告 (北京时间 09:00 或 22:00 触发一次)
            now_cn = datetime.now(CN_TZ)
            today_str = now_cn.strftime("%Y-%m-%d")
            if today_str != last_daily_report_day:
                if (now_cn.hour == 9 and now_cn.minute < 15) or (now_cn.hour == 22 and now_cn.minute < 15):
                    try:
                        await send_daily_portfolio_report()
                        last_daily_report_day = today_str
                    except Exception as e:
                        logger.error(f"[Scheduler] 每日报告触发异常: {e}")

            # 4.5 每日凌晨 03:00 数据保留清理（低峰期）
            if now_cn.hour == 3 and now_cn.minute < 5:
                try:
                    await purge_old_analysis_reports()
                except Exception as e:
                    logger.error(f"[Scheduler] 数据保留清理调用异常: {e}")

            # 4.7 自动刷新陈旧 AI 分析 (每 30 分钟检查一次，非阻塞)
            if datetime.now() - last_auto_analysis_refresh > timedelta(minutes=30):
                last_auto_analysis_refresh = datetime.now()
                asyncio.create_task(
                    _run_auto_analysis_bg_task(SessionLocal)
                )

            # 5. 盘后 AI 深度复盘 (每 15 分钟检查一次，内部有时间窗口过滤)
            try:
                await refresh_post_market_analysis()
            except Exception as e:
                logger.error(f"[Scheduler] 盘后复盘触发异常: {e}")

            # 6. 虚拟挂单模拟 (每 1 分钟检查一次)
            try:
                await refresh_simulated_trades()
            except Exception as e:
                logger.error(f"[Scheduler] 虚拟盯盘触发异常: {e}")

        finally:
            await release_lock(lock_key)

        await asyncio.sleep(60)  # 将精度从 5 分钟提升至 1 分钟
