import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.stock import MarketDataCache
from app.models.analysis import AnalysisReport
from app.services.market_data import MarketDataService
from app.services.notification_service import NotificationService

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
                            updated_data = await MarketDataService.get_real_time_data(t, local_db, force_refresh=True, skip_news=True)
                            
                            if updated_data:
                                # --- 检查价格触达与指标异动 (Check price hits & indicator alerts) ---
                                await check_and_notfy_alerts(t, updated_data, local_db)

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

async def check_and_notfy_alerts(ticker: str, current_data: MarketDataCache, db: AsyncSession):
    """
    检查价格与指标是否触发警报
    """
    try:
        # 1. 获取该用户对该股票的最新 AI 分析建议 (狙击位)
        # 注意：此处简单处理，获取该标的最后一份分析。
        stmt = select(AnalysisReport).where(AnalysisReport.ticker == ticker).order_by(AnalysisReport.created_at.desc()).limit(1)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        
        curr_price = current_data.current_price
        
        if report and curr_price:
            # 价格触达逻辑：如果价格涨过止盈位，或跌破止损位
            if report.target_price and curr_price >= report.target_price:
                await NotificationService.send_price_alert(ticker, ticker, curr_price, report.target_price, is_stop_loss=False)
            elif report.stop_loss_price and curr_price <= report.stop_loss_price:
                await NotificationService.send_price_alert(ticker, ticker, curr_price, report.stop_loss_price, is_stop_loss=True)
        
        # 2. 指标异动监控 (RSI 极端值)
        if current_data.rsi_14:
            if current_data.rsi_14 > 75:
                # 超买预警
                await NotificationService.send_feishu_card(
                    title=f"⚠️ 指标超买警报: {ticker}",
                    content=f"**{ticker}** RSI(14) 已飙升至 `{current_data.rsi_14:.2f}`，处于严重超买区间，风险正在积聚。",
                    color="red"
                )
            elif current_data.rsi_14 < 25:
                # 超卖预警
                await NotificationService.send_feishu_card(
                    title=f"🟢 指标超卖警报: {ticker}",
                    content=f"**{ticker}** RSI(14) 已跌至 `{current_data.rsi_14:.2f}`，处于严重超卖状态，可能存在技术性反弹机会。",
                    color="green"
                )
    except Exception as e:
        logger.error(f"Failed to check alerts for {ticker}: {e}")

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
            # 获取所有有持仓的用户及其 Email 进行个性化推送
            from app.models.portfolio import Portfolio
            from app.models.user import User
            
            # 使用 join 查询确保能拿到 email
            stmt = select(User.id, User.email).join(Portfolio, User.id == Portfolio.user_id).distinct()
            res = await db.execute(stmt)
            active_users = res.all() # 包含 (id, email) 的元组列表
            
            for user_id, email in active_users:
                summary_data = await MacroService.generate_hourly_news_summary(db, user_id)
                if summary_data.get("summary"):
                    await NotificationService.send_hourly_summary(
                        summary_text=summary_data["summary"],
                        count=summary_data["count"],
                        sentiment=summary_data.get("sentiment", "中性"),
                        email=email
                    )
        logger.info(f"[Scheduler] 已完成 {len(active_users)} 位用户的摘要生成与推送。")
    except Exception as e:
        logger.error(f"[Scheduler] 每小时新闻精要生成失败: {e}")

async def send_daily_portfolio_report():
    """生成并发送每日持仓健康报告 (Feishu Card)"""
    try:
        from app.models.stock import Portfolio
        from app.models.analysis import PortfolioAnalysisReport
        from app.services.ai_service import AIService
        from app.services.macro_service import MacroService
        
        async with SessionLocal() as db:
            # 1. 获取所有用户的持仓 (此处简化为获取全部活跃标的)
            stmt = select(Portfolio)
            res = await db.execute(stmt)
            portfolios = res.scalars().all()
            
            if not portfolios:
                return
            
            # 由于当前是单用户演示系统，我们直接统计全局持仓快照进行分析
            # 实际多用户系统需按 user_id 分组
            ticker_list = list(set([p.ticker for p in portfolios]))
            
            # 获取宏观背景
            macro_data = await MacroService.get_latest_radar(db)
            news_data = await MacroService.get_latest_news(db, limit=10)
            
            macro_context = ""
            if macro_data:
                macro_context += "\n### 全球异动雷达\n" + "\n".join([f"- {t.title}: {t.summary} (热度: {t.heat_score})" for t in macro_data])
            if news_data:
                macro_context += "\n### 实时快讯\n" + "\n".join([f"- {n.title}: {n.content[:100]}..." for n in news_data])

            # 调用 AI 生成全量分析 (此处直接复用 AIService 逻辑)
            # 注意：此处需要传入结构化的 portfolio 数据，此处略作简化
            portfolio_info = [{"ticker": p.ticker, "shares": p.shares} for p in portfolios]
            
            logger.info(f"[Scheduler] 正在为 {len(portfolio_info)} 个持仓标的生成每日 AI 诊断周报...")
            
            # 模拟生成逻辑 (为了演示，直接调用分析服务的核心 Prompt 逻辑)
            # 在实际生产中，应从 db 中查询最近一次分析，或重新触发 generate_portfolio_analysis
            analysis = await AIService.generate_portfolio_analysis(
                portfolio_data=portfolio_info,
                macro_context=macro_context
            )
            
            # 发送飞书消息
            # 提取 AI 返回的摘要信息 (简单从 Markdown 中提取或由 AI 返回结构化数据)
            # 此处演示通过富文本卡片展示
            await NotificationService.send_feishu_card(
                title="📅 每日持仓全景体检报告",
                content=f"**当前持仓摘要**:\n{analysis[:500]}...",
                color="blue"
            )
            logger.info("[Scheduler] 每日持仓报告推送成功。")
            
    except Exception as e:
        logger.error(f"[Scheduler] 每天报告生成失败: {e}")

async def start_scheduler():
    """
    启动常驻后台循环
    """
    logger.info("[Scheduler] 调度中心全面启动")
    
    # 记录各任务最后执行时间
    last_macro_update = datetime.min
    last_news_update = datetime.min
    last_headline_update = datetime.min
    last_hourly_summary_update = datetime.min
    last_daily_report_day = "" # 记录日期，防止一天多次触发
    
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

        # 2.5 每小时新闻摘要推送 (每小时定点)
        if datetime.now() - last_hourly_summary_update > timedelta(hours=1):
            try:
                await refresh_hourly_summary()
                last_hourly_summary_update = datetime.now()
            except Exception as e:
                logger.error(f"[Scheduler] 每小时摘要刷新异常: {e}")

        # 3. 宏观热点刷新 (每 5 小时尝试一次)
        if datetime.now() - last_macro_update > timedelta(hours=5):
            try:
                await refresh_macro_radar()
                last_macro_update = datetime.now()
            except Exception as e:
                logger.error(f"[Scheduler] 宏观刷新异常: {e}")
        
        # 4. 每日报告 (北京时间 09:00 或 22:00 触发一次)
        now_cn = datetime.now(CN_TZ)
        today_str = now_cn.strftime("%Y-%m-%d")
        if today_str != last_daily_report_day:
            # 在 09:00 - 09:15 或 22:00 - 22:15 之间触发
            if (now_cn.hour == 9 and now_cn.minute < 15) or (now_cn.hour == 22 and now_cn.minute < 15):
                try:
                    await send_daily_portfolio_report()
                    last_daily_report_day = today_str
                except Exception as e:
                    logger.error(f"[Scheduler] 每日报告触发异常: {e}")

        await asyncio.sleep(300) 
