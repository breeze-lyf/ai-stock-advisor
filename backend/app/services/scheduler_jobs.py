import asyncio
import logging
from datetime import datetime

import pytz

from app.application.analysis.analyze_portfolio import AnalyzePortfolioUseCase
from app.application.analysis.analyze_stock import AnalyzeStockUseCase
from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
from app.models.trade import TradeHistoryLog, TradeStatus
from app.services.macro_service import MacroService
from app.services.market_data import MarketDataService
from app.services.notification_service import NotificationService

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

            report = await repo.get_latest_analysis_report(user.id, ticker)
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
    semaphore = asyncio.Semaphore(3)

    async def safe_refresh(ticker: str):
        async with semaphore:
            try:
                await asyncio.sleep(1)
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

    for task in [safe_refresh(ticker) for ticker in active_tickers]:
        await task

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
            trade.exit_date = datetime.utcnow()
            trade.realized_pnl_pct = trade.unrealized_pnl_pct
            closed_count += 1
        elif trade.stop_loss_price and curr_price <= trade.stop_loss_price:
            trade.status = TradeStatus.CLOSED_LOSS
            trade.exit_price = curr_price
            trade.exit_date = datetime.utcnow()
            trade.realized_pnl_pct = trade.unrealized_pnl_pct
            closed_count += 1

        today = datetime.utcnow().date()
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
                    log_date=datetime.utcnow(),
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
            old_report = await repo.get_latest_analysis_report(user.id, portfolio.ticker)

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
