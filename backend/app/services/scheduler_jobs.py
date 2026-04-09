import asyncio
import logging
from datetime import datetime, timedelta

import pytz

from app.application.analysis.analyze_portfolio import AnalyzePortfolioUseCase
from app.application.analysis.analyze_stock import AnalyzeStockUseCase
from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
from app.models.trade import TradeHistoryLog, TradeStatus
from app.services.macro_service import MacroService
from app.services.market_data import MarketDataService
from app.services.notification_service import NotificationService
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)

CN_TZ = pytz.timezone("Asia/Shanghai")


def get_markets_to_process(now_utc: datetime) -> list[str]:
    markets_to_process = []
    cn_now = now_utc.astimezone(CN_TZ)

    if cn_now.hour == 15 and 30 <= cn_now.minute < 45:
        markets_to_process.append("A")

    if cn_now.hour == 16 and 30 <= cn_now.minute < 45:
        markets_to_process.append("HK")

    if cn_now.hour == 5 and 30 <= cn_now.minute < 45:
        markets_to_process.append("US")

    return markets_to_process


def resolve_market(ticker: str) -> str:
    if ticker.isdigit():
        return "A" if len(ticker) == 6 else "HK"
    if ticker.endswith(".HK"):
        return "HK"
    return "US"


async def build_macro_context(db, news_limit: int, include_heat: bool = False) -> str:
    macro_data = await MacroService.get_latest_radar(db)
    news_data = await MacroService.get_latest_news(db, limit=news_limit)

    macro_context = ""
    if macro_data:
        if include_heat:
            macro_context += "\n### 全球异动雷达\n" + "\n".join(
                [f"- {t.title}: {t.summary} (热度: {t.heat_score})" for t in macro_data]
            )
        else:
            macro_context += "\n### 全球异动雷达\n" + "\n".join([f"- {t.title}: {t.summary}" for t in macro_data])
    if news_data:
        macro_context += "\n### 实时快讯\n" + "\n".join([f"- {n.title}: {n.content[:100]}..." for n in news_data])
    return macro_context


def build_strategy_snapshot(report) -> dict:
    return {
        "action": getattr(report, "immediate_action", None),
        "target": getattr(report, "target_price", None),
        "stop_loss": getattr(report, "stop_loss_price", None),
        "rr_grade": getattr(report, "rr_ratio", None),
    }


def detect_strategy_change(old_strat: dict, new_strat: dict):
    if old_strat["action"] != new_strat["action"]:
        return True, f"建议操作由 [{old_strat['action']}] 调整为 [{new_strat['action']}]"

    if old_strat["target"] and new_strat["target"]:
        diff = abs(new_strat["target"] - old_strat["target"]) / old_strat["target"]
        if diff > 0.03:
            return True, f"目标价发生显著修正 (偏差 {diff:.1%})"

    if old_strat["stop_loss"] and new_strat["stop_loss"]:
        diff = abs(new_strat["stop_loss"] - old_strat["stop_loss"]) / old_strat["stop_loss"]
        if diff > 0.03:
            return True, f"止损位置需动态调整 (偏差 {diff:.1%})"

    return False, ""


async def check_and_notify_alerts_job(ticker: str, current_data, db):
    try:
        repo = SchedulerRepository(db)
        users = await repo.get_users_holding_ticker(ticker)
        if not users:
            return

        stock_name = await repo.get_stock_name(ticker)
        for user in users:
            if not user.feishu_webhook_url or not user.enable_price_alerts:
                continue

            report = await repo.get_latest_shared_analysis_report(ticker)
            curr_price = current_data.current_price

            if report and curr_price:
                if report.target_price and curr_price >= report.target_price:
                    await NotificationService.send_price_alert(
                        ticker,
                        stock_name,
                        curr_price,
                        report.target_price,
                        is_stop_loss=False,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url,
                    )
                elif report.stop_loss_price and curr_price <= report.stop_loss_price:
                    await NotificationService.send_price_alert(
                        ticker,
                        stock_name,
                        curr_price,
                        report.stop_loss_price,
                        is_stop_loss=True,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url,
                    )

            if current_data.rsi_14:
                if current_data.rsi_14 > 75:
                    await NotificationService.send_feishu_card(
                        title=f"⚠️ 指标超买警报: {stock_name}",
                        content=f"**{stock_name} ({ticker})** RSI(14) 已飙升至 `{current_data.rsi_14:.2f}`，处于严重超买区间。",
                        color="red",
                        msg_type="INDICATOR_ALERT",
                        ticker=ticker,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url,
                    )
                elif current_data.rsi_14 < 25:
                    await NotificationService.send_feishu_card(
                        title=f"🟢 指标超卖警报: {stock_name}",
                        content=f"**{stock_name} ({ticker})** RSI(14) 已跌至 `{current_data.rsi_14:.2f}`，处于严重超卖状态。",
                        color="green",
                        msg_type="INDICATOR_ALERT",
                        ticker=ticker,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url,
                    )
    except Exception as exc:
        logger.error(f"Failed to check multi-user alerts for {ticker}: {exc}")


async def run_refresh_all_stocks_job(db, should_refresh_fn, session_factory) -> int:
    repo = SchedulerRepository(db)
    caches = await repo.get_market_caches()
    if not caches:
        return 0

    active_tickers = [cache.ticker for cache in caches if should_refresh_fn(cache.ticker, cache.last_updated)]
    if not active_tickers:
        logger.debug("所有数据均已达到最新（包含盘后收盘价），跳过本轮刷新。")
        return 0

    logger.info(f"[Scheduler] 发现 {len(active_tickers)} 只股票需要更新（盘中或盘后补录），开始后台刷新...")
    # 优化：并发数从 1 提升到 3，配合 5 秒间隔，实现平滑请求流
    # 每秒约 0.6 个请求，避免触发 AkShare 反爬
    semaphore = asyncio.Semaphore(3)

    async def safe_refresh(ticker: str):
        async with semaphore:
            try:
                await asyncio.sleep(5)  # 增加到 5 秒，平滑请求分布
                async with session_factory() as local_db:
                    updated_data = await MarketDataService.get_real_time_data(
                        ticker,
                        local_db,
                        force_refresh=True,
                        skip_news=True,
                    )
                    if updated_data:
                        await check_and_notify_alerts_job(ticker, updated_data, local_db)
                logger.info(f"[Scheduler] 成功更新股票行情: {ticker}")
            except Exception as exc:
                logger.error(f"[Scheduler] 刷新 {ticker} 失败: {exc}")

    # 并行执行刷新任务 (使用信号量控制并发)
    await asyncio.gather(*[safe_refresh(ticker) for ticker in active_tickers])

    logger.info(f"[Scheduler] 本轮后台刷新成功完成，共更新 {len(active_tickers)} 只标的。")
    return len(active_tickers)


async def run_refresh_simulated_trades_job(db) -> tuple[int, int]:
    repo = SchedulerRepository(db)
    open_trades = await repo.get_open_simulated_trades()
    if not open_trades:
        return 0, 0

    updated_count = 0
    closed_count = 0

    for trade in open_trades:
        ticker = getattr(trade, "stock_ticker", None) or trade.ticker
        cache = await repo.get_market_cache(ticker)
        if not cache or cache.current_price is None:
            continue

        curr_price = cache.current_price
        trade.current_price = curr_price

        if trade.entry_price > 0:
            trade.unrealized_pnl_pct = ((curr_price - trade.entry_price) / trade.entry_price) * 100

        if trade.target_price and curr_price >= trade.target_price:
            trade.status = TradeStatus.CLOSED_PROFIT
            trade.exit_price = curr_price
            trade.exit_date = utc_now_naive()
            trade.realized_pnl_pct = trade.unrealized_pnl_pct
            closed_count += 1
        elif trade.stop_loss_price and curr_price <= trade.stop_loss_price:
            trade.status = TradeStatus.CLOSED_LOSS
            trade.exit_price = curr_price
            trade.exit_date = utc_now_naive()
            trade.realized_pnl_pct = trade.unrealized_pnl_pct
            closed_count += 1

        today = utc_now_naive().date()
        existing_log = await repo.get_today_trade_log(
            trade.id,
            datetime.combine(today, datetime.min.time()),
        )
        if existing_log:
            existing_log.price = curr_price
            existing_log.pnl_pct = trade.unrealized_pnl_pct
        else:
            repo.add_trade_log(
                TradeHistoryLog(
                    trade_id=trade.id,
                    log_date=utc_now_naive(),
                    price=curr_price,
                    pnl_pct=trade.unrealized_pnl_pct,
                )
            )

        updated_count += 1

    if updated_count > 0:
        await repo.save_changes()

    return updated_count, closed_count


async def run_post_market_analysis_job(db) -> list[str]:
    now_utc = datetime.now(pytz.utc)
    markets_to_process = get_markets_to_process(now_utc)
    if not markets_to_process:
        return []

    repo = SchedulerRepository(db)
    users = await repo.get_users_with_portfolios()
    macro_context = await build_macro_context(db, news_limit=20)

    for user in users:
        user_portfolios = await repo.get_user_portfolios(user.id)
        for portfolio in user_portfolios:
            if resolve_market(portfolio.ticker) not in markets_to_process:
                continue

            logger.info(f"[Scheduler] 正在复盘 {user.email} 的标的: {portfolio.ticker}")
            old_report = await repo.get_latest_shared_analysis_report(portfolio.ticker)

            try:
                analysis_result = await AnalyzeStockUseCase(db, user).execute(portfolio.ticker, force=True)
            except Exception as exc:
                logger.error(f"[Scheduler] 盘后复盘生成 {portfolio.ticker} 失败: {exc}")
                continue

            if not old_report or not user.feishu_webhook_url:
                continue

            old_strat = build_strategy_snapshot(old_report)
            new_strat = {
                "action": analysis_result.get("immediate_action"),
                "target": analysis_result.get("target_price"),
                "stop_loss": analysis_result.get("stop_loss_price"),
                "rr_grade": analysis_result.get("rr_ratio"),
            }
            significant_change, reason = detect_strategy_change(old_strat, new_strat)
            if not significant_change:
                continue

            stock_name = await repo.get_stock_name(portfolio.ticker)
            await NotificationService.send_strategy_change_alert(
                ticker=portfolio.ticker,
                name=stock_name,
                old_strategy=old_strat,
                new_strategy=new_strat,
                change_reason=reason,
                user_id=user.id,
                webhook_url=user.feishu_webhook_url,
            )

    return markets_to_process


async def run_daily_portfolio_report_job(db) -> int:
    repo = SchedulerRepository(db)
    users = await repo.get_users_with_daily_reports_enabled()
    if not users:
        return 0

    await build_macro_context(db, news_limit=10, include_heat=True)

    for user in users:
        user_portfolios = await repo.get_user_portfolios(user.id)
        if not user_portfolios:
            continue

        logger.info(f"[Scheduler] 正在为用户 {user.email} 生成持仓体检报告...")
        try:
            analysis = await AnalyzePortfolioUseCase(db, user).execute()
        except Exception as exc:
            logger.error(f"[Scheduler] 用户 {user.email} 每日报告生成失败: {exc}")
            continue

        await NotificationService.send_feishu_card(
            title="📅 每日持仓全景体检报告",
            content=f"**当前持仓摘要**:\n{analysis.detailed_report[:800]}...",
            color="blue",
            msg_type="DAILY_REPORT",
            user_id=user.id,
            webhook_url=user.feishu_webhook_url,
        )

    return len(users)


# ---------------------------------------------------------------------------
# 自动刷新陈旧分析 (Auto-refresh stale AI analysis)
# ---------------------------------------------------------------------------

def _is_market_open_for(ticker: str) -> bool:
    """轻量判断：当前是否处于该 ticker 的交易时段"""
    from datetime import time as dt_time
    import pytz as _pytz
    now_utc = datetime.now(_pytz.utc)
    ticker_up = ticker.upper()
    if ticker_up.isdigit() and len(ticker_up) == 6:  # A股
        tz = _pytz.timezone("Asia/Shanghai")
        t = now_utc.astimezone(tz).time()
        return (dt_time(9, 15) <= t <= dt_time(11, 30)) or (dt_time(13, 0) <= t <= dt_time(15, 0))
    elif ticker_up.endswith(".HK"):  # 港股
        tz = _pytz.timezone("Asia/Shanghai")
        t = now_utc.astimezone(tz).time()
        return (dt_time(9, 30) <= t <= dt_time(12, 0)) or (dt_time(13, 0) <= t <= dt_time(16, 0))
    else:  # 美股
        tz = _pytz.timezone("America/New_York")
        t = now_utc.astimezone(tz).time()
        return dt_time(9, 30) <= t <= dt_time(16, 0)


def should_auto_analyze(ticker: str, report) -> bool:
    """
    判断是否需要自动触发 AI 分析：
    - 从未分析过 → True
    - 盘中且分析超过 4 小时 → True
    - 盘外且分析超过 24 小时 → True
    """
    if report is None:
        return True
    age = datetime.utcnow() - report.created_at
    threshold = timedelta(hours=4) if _is_market_open_for(ticker) else timedelta(hours=24)
    return age > threshold


async def run_auto_refresh_stale_analysis_job(session_factory, max_per_run: int = 3) -> int:
    """
    扫描所有用户持仓 ticker，找出陈旧分析并自动触发 AI 更新。
    - 每次最多处理 max_per_run 个（成本保护）
    - AI 调用串行执行（避免并发爆破 LLM 限额）
    - 使用独立的数据库 session（不阻塞主调度循环）
    """
    stale: list[tuple[str, datetime | None]] = []

    async with session_factory() as db:
        repo = SchedulerRepository(db)
        tickers = await repo.get_all_portfolio_tickers()
        for ticker in tickers:
            report = await repo.get_latest_shared_analysis_report(ticker)
            if should_auto_analyze(ticker, report):
                age_h = None
                if report:
                    age_h = (datetime.utcnow() - report.created_at).total_seconds() / 3600
                stale.append((ticker, age_h))

    if not stale:
        logger.debug("[AutoRefresh] 所有持仓分析均为最新，跳过本轮")
        return 0

    # 按陈旧程度降序排列（未分析的 age=None 优先）
    stale.sort(key=lambda x: (x[1] is not None, -(x[1] or 0)))
    to_refresh = stale[:max_per_run]

    logger.info(f"[AutoRefresh] 发现 {len(stale)} 个陈旧分析，本轮处理 {len(to_refresh)} 个: "
                f"{[t for t, _ in to_refresh]}")

    refreshed = 0
    for ticker, age_h in to_refresh:
        async with session_factory() as db:
            try:
                repo = SchedulerRepository(db)
                users = await repo.get_users_holding_ticker(ticker)
                if not users:
                    continue
                age_str = f"{age_h:.1f}h" if age_h is not None else "未分析"
                logger.info(f"[AutoRefresh] 触发 {ticker} 分析 (陈旧度: {age_str})")
                await AnalyzeStockUseCase(db, users[0]).execute(ticker, force=True)
                refreshed += 1
            except Exception as exc:
                logger.error(f"[AutoRefresh] {ticker} 自动分析失败: {exc}")

    logger.info(f"[AutoRefresh] 本轮完成，成功更新 {refreshed}/{len(to_refresh)} 个分析")
    return refreshed


async def run_stock_capsule_refresh_job(session_factory) -> int:
    """
    Scan all portfolio tickers and refresh StockCapsules older than 24 h.
    Capsules that don't exist yet are also generated.
    AI calls are serialised to avoid rate-limit explosions.
    """
    from datetime import timezone
    from sqlalchemy import select
    from app.models.stock_capsule import StockCapsule
    from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase

    STALE_HOURS = 24
    refreshed = 0

    async with session_factory() as db:
        repo = SchedulerRepository(db)
        tickers = await repo.get_all_portfolio_tickers()

    if not tickers:
        return 0

    # Build a set of (ticker, type) that need refresh
    stale_keys: list[tuple[str, str]] = []
    async with session_factory() as db:
        stmt = select(StockCapsule).where(StockCapsule.ticker.in_(tickers))
        result = await db.execute(stmt)
        existing: dict[tuple[str, str], StockCapsule] = {
            (row.ticker, row.capsule_type): row for row in result.scalars().all()
        }

    cutoff = datetime.utcnow() - timedelta(hours=STALE_HOURS)
    for ticker in tickers:
        for ctype in ("news", "fundamental"):
            row = existing.get((ticker, ctype))
            if row is None or (row.updated_at and row.updated_at < cutoff):
                stale_keys.append((ticker, ctype))

    if not stale_keys:
        logger.debug("[CapsuleRefresh] All capsules are fresh, skipping.")
        return 0

    logger.info(f"[CapsuleRefresh] {len(stale_keys)} capsule(s) to refresh: {stale_keys[:10]}...")

    for ticker, ctype in stale_keys:
        async with session_factory() as db:
            try:
                use_case = GenerateStockCapsuleUseCase(db)
                if ctype == "news":
                    await use_case.generate_news_capsule(ticker)
                else:
                    await use_case.generate_fundamental_capsule(ticker)
                refreshed += 1
                logger.info(f"[CapsuleRefresh] ✅ {ticker}/{ctype} capsule refreshed.")
            except Exception as exc:
                logger.error(f"[CapsuleRefresh] ❌ {ticker}/{ctype} failed: {exc}")

    logger.info(f"[CapsuleRefresh] Done. Refreshed {refreshed}/{len(stale_keys)} capsules.")
    return refreshed
