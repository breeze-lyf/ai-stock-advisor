"""
Read-only agent tools. Every tool wraps an EXISTING service/use-case and is
scoped to the authenticated user carried in ToolContext.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-^=]{1,15}$")


class ToolError(Exception):
    """User-facing tool error (message is safe to show to the model)."""


@dataclass
class ToolContext:
    db: Any
    user: Any
    sources: list[dict] = field(default_factory=list)

    def add_source(self, title: str, url: Optional[str] = None, kind: str = "data"):
        item = {"title": title, "url": url, "kind": kind}
        if item not in self.sources and len(self.sources) < 50:
            self.sources.append(item)


@dataclass
class Tool:
    name: str
    title: str
    description: str
    parameters: dict
    handler: Callable[[ToolContext, dict], Awaitable[Any]]
    timeout: Optional[int] = None

    def openai_schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}

    def mcp_schema(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.parameters,
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True},
        }


def _norm_ticker(args: dict) -> str:
    t = str(args.get("ticker") or "").strip().upper()
    if not t or not _TICKER_RE.match(t):
        raise ToolError("参数 ticker 无效，例如 AAPL、0700.HK、600519")
    return t


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if hasattr(o, "model_dump"):
        return o.model_dump()
    return str(o)


def truncate_result(data: Any, max_chars: Optional[int] = None) -> str:
    max_chars = max_chars or settings.AGENT_TOOL_RESULT_MAX_CHARS
    text = json.dumps(data, ensure_ascii=False, default=_json_default)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 40] + f'..."[truncated {len(text) - max_chars + 40} chars]'


def _pick(obj: Any, fields: list[str]) -> dict:
    if obj is None:
        return {}
    return {f: getattr(obj, f, None) for f in fields if getattr(obj, f, None) is not None}


TICKER_PARAM = {"type": "string", "description": "股票代码：美股 AAPL，港股 0700.HK，A股 600519 / 600519.SS"}

# ---------------------------------------------------------------- handlers

_QUOTE_FIELDS = ["ticker", "current_price", "change_percent", "market_status", "last_updated"]
_TECH_FIELDS = [
    "rsi_14", "ma_20", "ma_50", "ma_200", "macd_val", "macd_signal", "macd_hist", "macd_cross",
    "bb_upper", "bb_middle", "bb_lower", "k_line", "d_line", "j_line", "atr_14", "adx_14",
    "volume_ratio", "pivot_point", "resistance_1", "support_1", "risk_reward_ratio",
]
_FUND_FIELDS = [
    "ticker", "name", "sector", "industry", "market_cap", "pe_ratio", "forward_pe", "eps",
    "dividend_yield", "beta", "fifty_two_week_high", "fifty_two_week_low", "earnings_date",
    "target_price_mean", "analyst_count", "analyst_buy_count", "analyst_hold_count",
    "analyst_sell_count", "exchange", "currency",
]


async def _market_cache(ctx: ToolContext, ticker: str, price_only: bool):
    from app.services.domain.market.market_data import MarketDataService

    return await MarketDataService.get_real_time_data(
        ticker,
        ctx.db,
        preferred_source=getattr(ctx.user, "preferred_data_source", None) or "AUTO",
        price_only=price_only,
        skip_news=True,
        user_id=ctx.user.id,
    )


async def get_quote(ctx: ToolContext, args: dict):
    ticker = _norm_ticker(args)
    cache = await _market_cache(ctx, ticker, price_only=True)
    if cache is None:
        raise ToolError(f"未获取到 {ticker} 行情")
    ctx.add_source(f"{ticker} 行情（系统行情缓存/多源 provider）")
    return _pick(cache, _QUOTE_FIELDS)


async def get_kline_and_technicals(ctx: ToolContext, args: dict):
    from app.services.integrations.market.market_providers import ProviderFactory

    ticker = _norm_ticker(args)
    period = args.get("period") or "6mo"
    if period not in {"1mo", "3mo", "6mo", "1y", "2y"}:
        period = "6mo"
    bars = max(5, min(int(args.get("bars") or 30), 60))
    cache = await _market_cache(ctx, ticker, price_only=False)
    ohlcv: list = []
    try:
        provider = ProviderFactory.get_provider(ticker, "AUTO")
        ohlcv = await provider.get_ohlcv(ticker, interval="1d", period=period) or []
    except Exception as e:
        logger.warning(f"agent kline fetch failed {ticker}: {e}")
    rows = []
    for r in ohlcv[-bars:]:
        d = r if isinstance(r, dict) else (r.model_dump() if hasattr(r, "model_dump") else vars(r))
        rows.append({k: d.get(k) for k in ("time", "date", "open", "high", "low", "close", "volume") if k in d})
    ctx.add_source(f"{ticker} 日K线 {period} + 技术指标")
    return {
        "ticker": ticker,
        "price": _pick(cache, ["current_price", "change_percent"]),
        "technicals": _pick(cache, _TECH_FIELDS),
        "daily_bars": rows,
        "bars_total": len(ohlcv),
    }


async def get_fundamentals(ctx: ToolContext, args: dict):
    from sqlalchemy import select
    from app.models.stock import Stock

    ticker = _norm_ticker(args)
    cache = await _market_cache(ctx, ticker, price_only=False)
    stock = (await ctx.db.execute(select(Stock).where(Stock.ticker == ticker))).scalar_one_or_none()
    if stock is None and cache is None:
        raise ToolError(f"未找到 {ticker} 基本面数据")
    ctx.add_source(f"{ticker} 基本面（provider 基本面 + 分析师一致预期）")
    out = _pick(stock, _FUND_FIELDS)
    out.update(_pick(cache, ["pe_percentile", "pb_percentile", "net_inflow"]))
    return out


async def search_news(ctx: ToolContext, args: dict):
    limit = max(1, min(int(args.get("limit") or 10), 20))
    query = (args.get("query") or "").strip()
    if args.get("ticker"):
        from app.infrastructure.db.repositories.stock_repository import StockRepository

        ticker = _norm_ticker(args)
        items = await StockRepository(ctx.db).get_latest_news(ticker, limit=limit * 2)
        news = [
            {"title": n.title, "publisher": n.publisher, "link": n.link, "time": n.publish_time, "summary": (n.summary or "")[:300]}
            for n in items
        ]
        label = f"{ticker} 个股新闻"
    else:
        from app.services.domain.macro.macro_service import MacroService

        items = await MacroService.get_latest_news(ctx.db, limit=100 if query else limit)
        news = [{"title": n.title, "time": n.published_at, "summary": (n.content or "")[:300]} for n in items]
        label = "财联社全球快讯"
    if query:
        q = query.lower()
        news = [n for n in news if q in f"{n.get('title') or ''} {n.get('summary') or ''}".lower()]
    news = news[:limit]
    for n in news[:5]:
        if n.get("link"):
            ctx.add_source(n.get("title") or label, n["link"], kind="news")
    ctx.add_source(label, kind="news")
    return {"source": label, "count": len(news), "items": news}


async def get_portfolio(ctx: ToolContext, args: dict):
    from app.application.portfolio.query_portfolio import GetPortfolioSummaryUseCase, GetPortfolioUseCase

    # Always the CURRENT user's portfolio; no user_id argument is accepted.
    items = await GetPortfolioUseCase(ctx.db, ctx.user).execute(refresh=False)
    summary = await GetPortfolioSummaryUseCase(ctx.db, ctx.user).execute()
    keep = ["ticker", "name", "quantity", "avg_cost", "current_price", "market_value", "unrealized_pl", "pl_percent", "sector"]
    holdings = []
    for it in items[:50]:
        d = it.model_dump() if hasattr(it, "model_dump") else dict(it)
        holdings.append({k: d.get(k) for k in keep})
    s = summary.model_dump() if hasattr(summary, "model_dump") else summary
    if isinstance(s, dict):
        s = {k: v for k, v in s.items() if k != "holdings"}
    ctx.add_source("我的持仓（本账户）")
    return {"summary": s, "holdings": holdings, "count": len(items)}


async def run_stock_diagnosis(ctx: ToolContext, args: dict):
    from app.application.analysis.analyze_stock import AnalyzeStockUseCase
    from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
    from app.services.ai_service import AIService

    ticker = _norm_ticker(args)
    use_case = AnalyzeStockUseCase(
        analysis_repo=AnalysisRepository(ctx.db),
        ai_service=AIService(db=ctx.db, user=ctx.user),
        current_user=ctx.user,
        db=ctx.db,
    )
    result = await use_case.execute(ticker=ticker, force=False)  # cached report reuse; free-tier limits apply
    if not isinstance(result, dict):
        result = result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
    ctx.add_source(f"{ticker} AI 深度诊断报告（系统单股诊断）", f"/?ticker={ticker}", kind="analysis")
    drop = {"raw_response", "prompt", "debug"}
    return {k: v for k, v in result.items() if k not in drop}


async def macro_snapshot(ctx: ToolContext, args: dict):
    from app.services.domain.macro.macro_service import MacroService

    topics = await MacroService.get_latest_radar(ctx.db)
    out = []
    for t in topics[:8]:
        ia = t.impact_analysis or {}
        out.append({
            "title": t.title,
            "heat": t.heat_score,
            "summary": (t.summary or "")[:300],
            "logic": (ia.get("logic") or "")[:300] if isinstance(ia, dict) else None,
            "beneficiaries": (ia.get("beneficiaries") or [])[:5] if isinstance(ia, dict) else None,
            "detriments": (ia.get("detriments") or [])[:5] if isinstance(ia, dict) else None,
            "updated_at": t.updated_at,
        })
    ctx.add_source("宏观雷达（系统宏观热点）")
    return {"topics": out}


TOOLS: list[Tool] = [
    Tool("get_quote", "实时报价", "获取单只股票最新价格与涨跌幅（A/H/US）。",
         {"type": "object", "properties": {"ticker": TICKER_PARAM}, "required": ["ticker"]}, get_quote),
    Tool("get_kline_and_technicals", "K线与技术指标",
         "获取日K线（最近 N 根）和技术指标（RSI/MACD/均线/布林/KDJ/ADX/支撑阻力）。",
         {"type": "object", "properties": {
             "ticker": TICKER_PARAM,
             "period": {"type": "string", "enum": ["1mo", "3mo", "6mo", "1y", "2y"], "description": "默认 6mo"},
             "bars": {"type": "integer", "minimum": 5, "maximum": 60, "description": "返回最近多少根日K，默认 30"},
         }, "required": ["ticker"]}, get_kline_and_technicals),
    Tool("get_fundamentals", "基本面", "获取估值、行业、市值、EPS、股息、Beta、52周区间、分析师评级与目标价。",
         {"type": "object", "properties": {"ticker": TICKER_PARAM}, "required": ["ticker"]}, get_fundamentals),
    Tool("search_news", "新闻检索", "检索个股新闻（传 ticker）或全球财经快讯（不传 ticker），可用 query 关键词过滤。",
         {"type": "object", "properties": {
             "ticker": TICKER_PARAM,
             "query": {"type": "string", "description": "关键词过滤，可空"},
             "limit": {"type": "integer", "minimum": 1, "maximum": 20},
         }}, search_news),
    Tool("get_portfolio", "我的持仓", "获取当前登录用户自己的持仓/自选列表与组合汇总（只读）。",
         {"type": "object", "properties": {}}, get_portfolio),
    Tool("run_stock_diagnosis", "AI 深度诊断",
         "调用系统已有的单股 AI 深度诊断（耗时较长，优先复用近期报告），返回操作建议、关键价位、风险与依据。仅在用户要求深度分析时使用。",
         {"type": "object", "properties": {"ticker": TICKER_PARAM}, "required": ["ticker"]}, run_stock_diagnosis, timeout=170),
    Tool("macro_snapshot", "宏观快照", "获取最新的宏观热点雷达（主题、热度、受益/受损标的）。",
         {"type": "object", "properties": {}}, macro_snapshot),
]
TOOL_MAP = {t.name: t for t in TOOLS}


async def execute_tool(name: str, args: Any, ctx: ToolContext) -> tuple[bool, str]:
    """Run a tool safely. Returns (ok, json_text) — never raises."""
    tool = TOOL_MAP.get(name)
    if tool is None:
        return False, json.dumps({"error": f"未知工具 {name}"}, ensure_ascii=False)
    if ctx.user is None:
        return False, json.dumps({"error": "未认证"}, ensure_ascii=False)
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError:
            return False, json.dumps({"error": "参数不是合法 JSON"}, ensure_ascii=False)
    if not isinstance(args, dict):
        args = {}
    args.pop("user_id", None)  # never allow cross-user scoping
    try:
        data = await asyncio.wait_for(tool.handler(ctx, args), timeout=tool.timeout or settings.AGENT_TOOL_TIMEOUT_SECONDS)
        return True, truncate_result(data)
    except ToolError as e:
        return False, json.dumps({"error": str(e)}, ensure_ascii=False)
    except asyncio.TimeoutError:
        return False, json.dumps({"error": f"工具 {name} 超时"}, ensure_ascii=False)
    except Exception as e:
        logger.exception(f"agent tool {name} failed")
        try:
            await ctx.db.rollback()  # keep the session usable for later tools/persistence
        except Exception:
            pass
        return False, json.dumps({"error": f"工具 {name} 执行失败: {e.__class__.__name__}"}, ensure_ascii=False)
