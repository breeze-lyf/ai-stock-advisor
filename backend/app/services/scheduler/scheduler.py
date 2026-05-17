import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from app.core.database import SessionLocal
from app.core.config import settings
from app.services.scheduler.scheduler_jobs import (
    run_daily_portfolio_report_job,
    run_post_market_analysis_job,
    run_refresh_all_stocks_job,
    run_refresh_simulated_trades_job,
    run_auto_refresh_stale_analysis_job,
    run_stock_capsule_refresh_job,
)

from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
from app.services.domain.notifications.notification_service_v2 import NotificationServiceV2

logger = logging.getLogger(__name__)

# 统一使用 UTC 感知的时间
UTC = pytz.utc
CN_TZ = pytz.timezone("Asia/Shanghai")
US_TZ = pytz.timezone("America/New_York")


async def purge_old_analysis_reports():
    """删除超过 DATA_RETENTION_DAYS 天的分析报告，控制数据库体积。"""
    cutoff = datetime.now(UTC) - timedelta(days=settings.DATA_RETENTION_DAYS)
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
    async with SessionLocal() as db:
        try:
            updated_count, closed_count = await run_refresh_simulated_trades_job(db)
            if updated_count > 0:
                logger.info(f"[Scheduler] 完成了 {updated_count} 笔虚拟订单盯盘。其中 {closed_count} 笔触点平仓。")
        except Exception as e:
            logger.error(f"[Scheduler] 虚拟盯盘服务异常: {e}")


def should_refresh(ticker: str, last_updated: datetime) -> bool:
    """
    基于 UTC 时间的开盘/收盘判定。
    修复：全部使用 UTC 感知时间，不再混用 naive 和 aware 时间。
    """
    now_utc = datetime.now(UTC)
    ticker = ticker.upper()

    def get_last_session_end(tz, close_hour, close_min):
        now_local = now_utc.astimezone(tz)
        today_close = now_local.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)

        if today_close.weekday() == 5:
            today_close -= timedelta(days=1)
        elif today_close.weekday() == 6:
            today_close -= timedelta(days=2)

        if now_local < today_close:
            days_back = 1
            if today_close.weekday() == 0:
                days_back = 3
            today_close -= timedelta(days=days_back)

        return today_close

    # 确定市场参数
    now_cn = now_utc.astimezone(CN_TZ)
    now_us = now_utc.astimezone(US_TZ)

    if ticker.isdigit() and len(ticker) == 6:  # A股
        tz, close_h, close_m = CN_TZ, 15, 0
        market_open = (time(9, 15) <= now_cn.time() <= time(11, 30)) or \
                      (time(13, 0) <= now_cn.time() <= time(15, 0))
    elif (ticker.isdigit() and len(ticker) == 5) or ticker.endswith(".HK"):  # 港股
        tz, close_h, close_m = CN_TZ, 16, 0
        market_open = (time(9, 30) <= now_cn.time() <= time(12, 0)) or \
                      (time(13, 0) <= now_cn.time() <= time(16, 0))
    else:  # 美股
        tz, close_h, close_m = US_TZ, 16, 0
        market_open = time(9, 30) <= now_us.time() <= time(16, 0)

    # 确保 last_updated 是 UTC-aware
    if last_updated.tzinfo is None:
        last_updated = UTC.localize(last_updated)

    # 开盘中：数据超过 5 分钟则刷新
    if market_open:
        return (now_utc - last_updated) > timedelta(minutes=5)

    # 休市：检查最后更新时间是否早于最近一次收盘时间
    last_session_end = get_last_session_end(tz, close_h, close_m)
    return last_updated < last_session_end


async def refresh_all_stocks():
    async with SessionLocal() as db:
        try:
            await run_refresh_all_stocks_job(db, should_refresh, SessionLocal)
        except Exception as e:
            logger.error(f"[Scheduler] 轮询任务发生异常: {e}")


from app.services.domain.macro.macro_service import MacroService


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

            for user in active_users:
                summary_data = await MacroService.generate_hourly_news_summary(db, user.id)
                if summary_data.get("summary"):
                    await NotificationServiceV2.send_hourly_summary(
                        user_id=user.id,
                        summary_text=summary_data["summary"],
                        count=summary_data["count"],
                        sentiment=summary_data.get("sentiment", "中性"),
                        email=user.email,
                        hour_key=summary_data.get("hour_key"),
                    )
        logger.info(f"[Scheduler] 已完成 {len(active_users)} 位用户的摘要生成与推送。")
    except Exception as e:
        logger.error(f"[Scheduler] 每小时新闻精要生成失败: {e}")


async def refresh_post_market_analysis():
    try:
        async with SessionLocal() as db:
            markets_to_process = await run_post_market_analysis_job(db)
        if not markets_to_process:
            return
        logger.info(f"[Scheduler] 盘后复盘任务处理完成: {markets_to_process}")
    except Exception as e:
        logger.error(f"[Scheduler] 盘后复盘任务失败: {e}")


async def send_daily_portfolio_report():
    try:
        async with SessionLocal() as db:
            users_count = await run_daily_portfolio_report_job(db)
            logger.info(f"[Scheduler] 已完成 {users_count} 位用户的持仓报告推送。")
    except Exception as e:
        logger.error(f"[Scheduler] 每天报告生成失败: {e}")


async def _run_auto_analysis_bg_task(session_factory):
    try:
        count = await run_auto_refresh_stale_analysis_job(session_factory)
        if count:
            logger.info(f"[AutoRefresh] 本轮完成 {count} 个标的的自动分析刷新")
    except Exception as e:
        logger.error(f"[AutoRefresh] 后台分析刷新任务异常: {e}")


async def _run_capsule_refresh_bg_task(session_factory):
    try:
        count = await run_stock_capsule_refresh_job(session_factory)
        if count:
            logger.info(f"[CapsuleRefresh] 本轮刷新了 {count} 个 capsule")
    except Exception as e:
        logger.error(f"[CapsuleRefresh] 后台 capsule 刷新任务异常: {e}")


async def start_scheduler():
    """
    启动常驻后台循环。
    修复：全部使用 UTC 感知时间，消除 datetime.now() 与 datetime.now(CN_TZ) 混用。
    """
    logger.info("[Scheduler] 调度中心全面启动，轮询精度：60s")

    last_news_update = datetime.now(UTC) - timedelta(minutes=5)
    last_headline_update = datetime.now(UTC) - timedelta(hours=3)
    last_triggered_summary_hour = -1
    last_daily_report_day = ""
    last_auto_analysis_refresh = datetime.now(UTC) - timedelta(minutes=30)
    last_capsule_refresh = datetime.now(UTC) - timedelta(hours=23)

    while True:
        from app.core.redis_client import acquire_lock, release_lock
        lock_key = "scheduler:cycle_lock"
        if not await acquire_lock(lock_key, ttl=55):
            logger.debug("[Scheduler] Another instance holds the cycle lock, skipping cycle.")
            await asyncio.sleep(60)
            continue

        try:
            now_utc = datetime.now(UTC)
            now_cn = now_utc.astimezone(CN_TZ)

            # 1. 股票行情刷新
            try:
                await refresh_all_stocks()
            except Exception as e:
                logger.error(f"[Scheduler] 股票行情刷新异常: {e}")

            # 2. 财联社全球快讯 (每 10 分钟)
            if now_utc - last_news_update > timedelta(minutes=10):
                try:
                    await refresh_cls_news()
                    last_news_update = now_utc
                except Exception as e:
                    logger.error(f"[Scheduler] 财联社刷新异常: {e}")

            # 2.5 每小时综合推送 (整点对齐)
            if now_cn.minute < 15 and now_cn.hour != last_triggered_summary_hour:
                try:
                    logger.info(f"[Scheduler] 整点窗口 ({now_cn.strftime('%H:%M')}), 执行每小时推送任务...")
                    await refresh_macro_radar()
                    await refresh_hourly_summary()
                    last_triggered_summary_hour = now_cn.hour
                except Exception as e:
                    logger.error(f"[Scheduler] 整点推送触发异常: {e}")

            # 3. 财联社深度头条 (每 4 小时)
            if now_utc - last_headline_update > timedelta(hours=4):
                try:
                    await refresh_cls_headlines()
                    last_headline_update = now_utc
                except Exception as e:
                    logger.error(f"[Scheduler] 深度头条刷新异常: {e}")

            # 4. 每日报告 (北京时间 09:00 或 22:00)
            today_str = now_cn.strftime("%Y-%m-%d")
            if today_str != last_daily_report_day:
                if (now_cn.hour == 9 and now_cn.minute < 15) or (now_cn.hour == 22 and now_cn.minute < 15):
                    try:
                        await send_daily_portfolio_report()
                        last_daily_report_day = today_str
                    except Exception as e:
                        logger.error(f"[Scheduler] 每日报告触发异常: {e}")

            # 4.5 数据保留清理 (凌晨 03:00 北京时间)
            if now_cn.hour == 3 and now_cn.minute < 5:
                try:
                    await purge_old_analysis_reports()
                except Exception as e:
                    logger.error(f"[Scheduler] 数据保留清理调用异常: {e}")

            # 4.7 自动刷新陈旧 AI 分析 (每 30 分钟)
            if now_utc - last_auto_analysis_refresh > timedelta(minutes=30):
                last_auto_analysis_refresh = now_utc
                asyncio.create_task(_run_auto_analysis_bg_task(SessionLocal))

            # 4.8 StockCapsule 24h 预计算刷新
            if now_utc - last_capsule_refresh > timedelta(hours=24):
                last_capsule_refresh = now_utc
                asyncio.create_task(_run_capsule_refresh_bg_task(SessionLocal))

            # 5. 盘后 AI 深度复盘
            try:
                await refresh_post_market_analysis()
            except Exception as e:
                logger.error(f"[Scheduler] 盘后复盘触发异常: {e}")

            # 6. 虚拟挂单模拟
            try:
                await refresh_simulated_trades()
            except Exception as e:
                logger.error(f"[Scheduler] 虚拟盯盘触发异常: {e}")

        finally:
            await release_lock(lock_key)

        await asyncio.sleep(60)
