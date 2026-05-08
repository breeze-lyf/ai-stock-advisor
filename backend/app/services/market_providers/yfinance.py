from __future__ import annotations

import asyncio
import logging
import httpx
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from yfinance.config import YfConfig

from app.schemas.market_data import MarketStatus, OHLCVItem, ProviderFundamental, ProviderNews, ProviderQuote, FullMarketData, ProviderTechnical
from app.services.indicators import TechnicalIndicators
from app.services.market_providers.base import MarketDataProvider
from app.utils.time import utc_now_naive
from app.core.config import settings

logger = logging.getLogger(__name__)

# 代理环境变量列表
_PROXY_ENV_VARS = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'NO_PROXY']

# 是否启用系统代理（通过环境变量控制）
_USE_SYSTEM_PROXY = os.environ.get("YFINANCE_USE_PROXY", "").lower() in ("1", "true", "yes")

# 配置 yfinance 使用代理（走 mihomo/clash 海外节点绕过阿里云 IP 限频）
_http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
if _USE_SYSTEM_PROXY and _http_proxy:
    proxy_config = {"http": _http_proxy, "https": _http_proxy}
    YfConfig.network.proxy = proxy_config
    logger.info(f"[YFinance] Configured proxy: {_http_proxy}")

# 类级别缓存：info 结果（60s TTL），VIX（5min TTL）
_info_cache: dict[str, tuple[Any, float]] = {}
_vix_cache: tuple[Optional[float], float] = (None, 0.0)
_INFO_CACHE_TTL = 60
_VIX_CACHE_TTL = 300


def _retry_with_backoff(max_retries=2, base_delay=2.0):
    """重试装饰器：指数退避 2s → 4s"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if "Too Many Requests" in str(exc) or "rate" in str(exc).lower():
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"YFinance rate limited, retry {attempt+1}/{max_retries} after {delay}s")
                        time.sleep(delay)
                    else:
                        raise
            raise last_exc
        return wrapper
    return decorator


def _disable_proxy_env():
    """临时禁用代理环境变量，返回原始值。
    当 YFINANCE_USE_PROXY=1 时保留代理设置，让 yfinance 走系统代理。
    """
    if _USE_SYSTEM_PROXY:
        return {}
    old_vals = {var: os.environ.pop(var, None) for var in _PROXY_ENV_VARS}
    return old_vals


def _restore_proxy_env(old_vals: dict):
    """恢复代理环境变量"""
    for var, val in old_vals.items():
        if val is not None:
            os.environ[var] = val


class YFinanceProvider(MarketDataProvider):
    PERIOD_MAP = {
        "1mo": "1mo",
        "3mo": "3mo",
        "6mo": "6mo",
        "1y": "1y",
        "5y": "5y",
        "200d": "1y",
    }

    INTERVAL_MAP = {
        "1d": "1d",
        "1h": "1h",
        "1wk": "1wk",
        "1mo": "1mo",
    }

    # Cloudflare Worker 代理配置 (可选)
    _worker_url: Optional[str] = getattr(settings, "CLOUDFLARE_WORKER_URL", None)
    _worker_key: Optional[str] = getattr(settings, "CLOUDFLARE_WORKER_KEY", None)

    # 类变量：记录是否需要使用 Worker 代理
    # 配置了 Worker URL 时默认启用；否则直连失败后切换
    _use_worker_proxy: bool = getattr(settings, "CLOUDFLARE_WORKER_URL", None) is not None

    # 类级别熔断器：限频时阻止后续所有请求
    _rate_limited_until: float = 0.0
    _RATE_LIMIT_COOLDOWN = 60  # 限频后冷却 60 秒

    @classmethod
    def get_proxy_status(cls) -> bool:
        """获取当前代理状态"""
        return cls._use_worker_proxy

    @classmethod
    def reset_proxy_flag(cls) -> None:
        """重置代理标志，恢复直连模式"""
        cls._use_worker_proxy = False
        logger.info("[YFinance] Proxy flag reset, resuming direct connection")

    @classmethod
    def is_rate_limited(cls) -> bool:
        """检查是否处于限频冷却期"""
        return time.time() < cls._rate_limited_until

    @classmethod
    def _activate_rate_limit_cooldown(cls):
        """触发限频冷却，30 秒内拒绝新请求"""
        cls._rate_limited_until = time.time() + cls._RATE_LIMIT_COOLDOWN
        logger.warning(f"[YFinance] Rate limit circuit breaker activated, {cls._RATE_LIMIT_COOLDOWN}s cooldown")

    @staticmethod
    def _get_cached_info(symbol: str, ticker_obj=None) -> dict[str, Any]:
        """获取缓存的 .info 结果，避免同一 symbol 重复请求 Yahoo 同一端点"""
        now = time.time()
        if symbol in _info_cache:
            cached_val, cached_time = _info_cache[symbol]
            if now - cached_time < _INFO_CACHE_TTL:
                return cached_val
        # Cache miss — fetch fresh (with calendar & recommendations if ticker available)
        info = dict(getattr(ticker_obj, "info", {}) or {}) if ticker_obj else {}
        if info and ticker_obj:
            # 额外拉取日历和推荐信息（只在 cache miss 时执行）
            try:
                cal = ticker_obj.calendar
                if cal is not None and isinstance(cal, dict):
                    earn = cal.get("Earnings Date")
                    if earn is not None:
                        if isinstance(earn, list) and len(earn) > 0:
                            info["_earnings_date"] = str(earn[0])[:10]
                        else:
                            info["_earnings_date"] = str(earn)[:10]
            except Exception:
                pass
            try:
                rec = ticker_obj.recommendations_summary
                if rec is not None and hasattr(rec, "itertuples") and len(rec) > 0:
                    latest = rec.iloc[0]
                    info["_analyst_buy"] = int(getattr(latest, "strongBuy", 0) or 0) + int(getattr(latest, "buy", 0) or 0)
                    info["_analyst_hold"] = int(getattr(latest, "hold", 0) or 0)
                    info["_analyst_sell"] = int(getattr(latest, "sell", 0) or 0) + int(getattr(latest, "strongSell", 0) or 0)
            except Exception:
                pass
            _info_cache[symbol] = (info, now)
        return info

    @staticmethod
    def _get_cached_vix() -> Optional[float]:
        """进程级 VIX 缓存，5 分钟 TTL"""
        now = time.time()
        global _vix_cache
        cached_val, cached_time = _vix_cache
        if now - cached_time < _VIX_CACHE_TTL and cached_val is not None:
            return cached_val
        try:
            vix_info = dict(getattr(yf.Ticker("^VIX"), "info", {}) or {})
            price = vix_info.get("regularMarketPrice") or vix_info.get("previousClose")
            result = float(price) if price is not None else None
            _vix_cache = (result, now)
            return result
        except Exception:
            return cached_val

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        symbol = ticker.upper().strip()
        if symbol == ".INX":
            return "^GSPC"
        if symbol == ".IXIC":
            return "^IXIC"
        if symbol == ".DJI":
            return "^DJI"
        return symbol

    @staticmethod
    def _market_status_from_info(info: dict[str, Any]) -> MarketStatus:
        quote_type = str(info.get("quoteType") or "").upper()
        state = str(info.get("marketState") or "").upper()
        if "PRE" in state:
            return MarketStatus.PRE_MARKET
        if "POST" in state or "AFTER" in state:
            return MarketStatus.AFTER_HOURS
        if "OPEN" in state or quote_type == "EQUITY":
            return MarketStatus.OPEN
        return MarketStatus.CLOSED

    async def _run_sync(self, func, *args, **kwargs):
        """运行同步函数，自动禁用代理环境变量"""
        def wrapped():
            old_vals = _disable_proxy_env()
            try:
                return func(*args, **kwargs)
            finally:
                _restore_proxy_env(old_vals)
        return await asyncio.to_thread(wrapped)

    async def search_instruments(self, query: str, limit: int = 20) -> list[dict[str, str]]:
        """
        搜索金融工具

        Args:
            query: 搜索关键词（股票代码、公司名称等）
            limit: 最大返回结果数量（默认 20，最多返回 Yahoo 返回的全部结果）

        Returns:
            搜索结果列表，每个结果包含 ticker 和 name 字段
        """
        normalized = (query or "").strip()
        if not normalized:
            return []

        # 接受的 quote type 列表 - 扩展以包含更多市场类型
        # EQUITY: 普通股
        # ETF: 交易所交易基金
        # MUTUALFUND: 共同基金
        # INDEX: 指数（如 ^GSPC, ^IXIC）
        # CURRENCY: 货币对
        # CRYPTOCURRENCY: 加密货币
        # FUTURE: 期货
        # MARKET: 市场指数
        ACCEPTED_QUOTE_TYPES = {"EQUITY", "ETF", "MUTUALFUND", "INDEX", "CURRENCY", "CRYPTOCURRENCY", "FUTURE", "MARKET"}

        try:
            def run_search() -> list[dict[str, Any]]:
                # 增加 max_results 以获取更多候选结果
                # Yahoo 实际返回的结果可能少于 max_results，所以设置大一点更安全
                search = yf.Search(
                    normalized,
                    max_results=max(limit, 30),  # 至少请求 30 条，确保足够筛选
                    news_count=0,
                    lists_count=0,
                    recommended=max(limit, 30),
                    include_cb=False,
                    enable_fuzzy_query=True,
                    raise_errors=False,
                )
                return list(getattr(search, "quotes", []) or [])

            quotes = await self._run_sync(run_search)
            results: list[dict[str, str]] = []
            seen: set[str] = set()

            for item in quotes:
                ticker = str(item.get("symbol") or "").strip().upper()
                if not ticker or ticker in seen:
                    continue

                quote_type = str(item.get("quoteType") or "").upper()
                # 放宽过滤条件：如果没有 quote_type 信息，也保留该结果（某些市场可能不返回此字段）
                if quote_type and quote_type not in ACCEPTED_QUOTE_TYPES:
                    logger.debug(f"YFinance search: skipping {ticker} with quote_type={quote_type}")
                    continue

                name = (
                    str(item.get("shortname") or "").strip()
                    or str(item.get("longname") or "").strip()
                    or ticker
                )
                seen.add(ticker)
                results.append({"ticker": ticker, "name": name})
                if len(results) >= limit:
                    break

            logger.debug(f"YFinance search for '{query}': found {len(results)} results (requested {limit})")
            return results
        except Exception as exc:
            logger.warning(f"YFinance search_instruments failed for {query}: {exc}")
            return []

    def _history_to_dataframe(self, history: pd.DataFrame) -> Optional[pd.DataFrame]:
        if history is None or history.empty:
            return None

        df = history.copy()
        df = df.reset_index()
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(
            columns={
                date_col: "Date",
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Volume": "Volume",
            }
        )
        keep_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        df = df[[col for col in keep_cols if col in df.columns]]
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Date", "Close"]).drop_duplicates(subset=["Date"]).sort_values("Date")
        return df

    async def _get_history_df(self, ticker: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
        symbol = self._normalize_ticker(ticker)
        yf_period = self.PERIOD_MAP.get(period, "1y")
        yf_interval = self.INTERVAL_MAP.get(interval, "1d")

        # 如果已标记需要使用 Worker 代理，直接使用
        if self._use_worker_proxy and self._worker_url and self._worker_key:
            df = await self._get_history_df_via_worker(symbol, yf_period, yf_interval)
            if df is not None and not df.empty:
                return df

        # 默认优先尝试 yfinance 直连
        try:
            history = await self._run_sync(lambda: yf.Ticker(symbol).history(
                period=yf_period, interval=yf_interval, auto_adjust=False, actions=False
            ))
            df = self._history_to_dataframe(history)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[YFinance] Direct yfinance failed for {ticker}: {e}")
            # 直连失败，标记需要使用 Worker 代理
            self._use_worker_proxy = True
            logger.info("[YFinance] Switching to Cloudflare Worker proxy for subsequent requests")

        # 直连失败或无数据，尝试 Worker 代理
        if self._worker_url and self._worker_key:
            try:
                df = await self._get_history_df_via_worker(symbol, yf_period, yf_interval)
                if df is not None and not df.empty:
                    self._use_worker_proxy = True
                    logger.info(f"[YFinance] Successfully fetched {ticker} via Cloudflare Worker")
                    return df
            except Exception as e:
                logger.warning(f"[YFinance] Worker proxy also failed for {ticker}: {e}")

        return None

    # Class-level cache for Worker crumb (shared across all requests)
    _worker_crumb: Optional[str] = None
    _worker_cookie: Optional[str] = None
    _worker_auth_expires: float = 0.0

    async def _proxy_via_worker(self, yahoo_url: str, method: str = "GET", body: Optional[dict] = None) -> Optional[Any]:
        """通用 Worker 代理：支持所有 Yahoo Finance API 端点。

        Worker 自动处理 Yahoo crumb 认证，客户端无需关心 auth 流程。
        """
        if not self._worker_url or not self._worker_key:
            return None

        try:
            worker_base = self._worker_url.rstrip("/")
            # 构建 Worker 请求 URL
            worker_url = f"{worker_base}/?url={httpx.URL(yahoo_url)}"
            headers = {"X-Proxy-Key": self._worker_key}

            async with httpx.AsyncClient(timeout=15.0) as client:
                if method == "POST":
                    response = await client.post(worker_url, headers=headers, json=body)
                else:
                    response = await client.get(worker_url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"[Worker] HTTP {response.status_code}: {yahoo_url[:80]}")
                    return None

                return response.json()
        except Exception as e:
            logger.debug(f"[Worker] Error: {e}")
            return None

    async def _get_history_df_via_worker(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        通过 Cloudflare Worker 代理获取 Yahoo 历史数据
        """
        if not self._worker_url or not self._worker_key:
            return None

        # 构建 Yahoo Finance Chart API URL
        yahoo_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={period}"

        try:
            data = await self._proxy_via_worker(yahoo_url)
            if not data:
                return None

            # 解析 Yahoo Chart API 响应
            result = data.get("chart", {}).get("result", [])
            if not result:
                return None

            quote = result[0]
            timestamps = quote.get("timestamp", [])
            ind = quote.get("indicators", {}).get("quote", [{}])[0]

            if not timestamps:
                return None

            # 构建 DataFrame
            df = pd.DataFrame({
                "Date": pd.to_datetime(timestamps, unit='s'),
                "Open": ind.get("open", []),
                "High": ind.get("high", []),
                "Low": ind.get("low", []),
                "Close": ind.get("close", []),
                "Volume": ind.get("volume", []),
            })

            # 清理数据
            df = df.dropna(subset=["Close"])
            df.set_index("Date", inplace=True)

            return df if not df.empty else None

        except Exception as e:
            logger.warning(f"[Worker] Error for {symbol}: {e}")
            return None

    async def _get_quote_summary_via_worker(self, symbol: str) -> Optional[dict]:
        """通过 Worker 获取 quoteSummary（info 数据来源）"""
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            f"?modules=financialData,quoteType,defaultKeyStatistics,assetProfile,summaryDetail"
            f"&symbol={symbol}"
        )
        data = await self._proxy_via_worker(url)
        if not data:
            return None
        result = data.get("quoteSummary", {}).get("result", [])
        return result[0] if result else None

    async def _get_recommendations_via_worker(self, symbol: str) -> Optional[dict]:
        """通过 Worker 获取 analyst recommendations"""
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            f"?modules=recommendationTrend&symbol={symbol}"
        )
        data = await self._proxy_via_worker(url)
        if not data:
            return None
        result = data.get("quoteSummary", {}).get("result", [])
        return result[0] if result else None

    async def _get_calendar_via_worker(self, symbol: str) -> Optional[dict]:
        """通过 Worker 获取 calendar events（earnings date 等）"""
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            f"?modules=calendarEvents&symbol={symbol}"
        )
        data = await self._proxy_via_worker(url)
        if not data:
            return None
        result = data.get("quoteSummary", {}).get("result", [])
        return result[0] if result else None

    async def _get_v7_quote_via_worker(self, symbol: str) -> Optional[dict]:
        """通过 Worker 获取 v7/finance/quote（快速行情）"""
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        data = await self._proxy_via_worker(url)
        if not data:
            return None
        result = data.get("quoteResponse", {}).get("result", [])
        return result[0] if result else None

    async def _get_news_via_worker(self, symbol: str) -> Optional[list]:
        """通过 Worker 获取新闻（POST 到 finance.yahoo.com/xhr/ncp）"""
        url = "https://finance.yahoo.com/xhr/ncp?queryRef=latestNews&serviceKey=ncp_fin"
        data = await self._proxy_via_worker(
            url,
            method="POST",
            body={"serviceConfig": {"snippetCount": 10, "s": [symbol]}}
        )
        if not data:
            return None
        return data.get("data", {}).get("content", {}).get("stream", [])

    def _parse_quote_summary_to_info(self, qs: dict) -> dict:
        """将 quoteSummary 结果解析为 yfinance .info 兼容格式"""
        info = {}
        modules = {
            "financialData": ["currentPrice", "targetMeanPrice", "numberOfAnalystOpinions",
                              "trailingPE", "forwardPE", "dividendYield", "beta", "marketCap",
                              "trailingEps", "returnOnEquity", "revenueGrowth", "earningsGrowth",
                              "grossMargins", "operatingMargins", "profitMargins",
                              "totalDebt", "totalRevenue", "debtToEquity", "returnOnAssets"],
            "quoteType": ["symbol", "shortName", "longName", "quoteType", "sector", "industry",
                          "marketState", "exchange", "currency"],
            "defaultKeyStatistics": ["marketCap", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
                                     "sharesOutstanding", "heldPercentInsiders",
                                     "heldPercentInstitutions"],
            "assetProfile": ["sector", "industry", "longBusinessSummary",
                             "city", "state", "country", "fullTimeEmployees"],
            "summaryDetail": ["regularMarketPrice", "regularMarketPreviousClose",
                              "regularMarketDayHigh", "regularMarketDayLow",
                              "regularMarketVolume", "averageVolume", "fiftyDayAverage",
                              "twoHundredDayAverage", "trailingPE", "forwardPE",
                              "dividendYield", "beta", "marketCap", "priceToBook",
                              "earningsQuarterlyGrowth"],
        }
        for module_name, fields in modules.items():
            module_data = qs.get(module_name, {})
            if not module_data:
                continue
            for field in fields:
                val = module_data.get(field)
                if val is not None:
                    # Unwrap Yahoo API nested values
                    if isinstance(val, dict) and "raw" in val:
                        val = val["raw"]
                    elif isinstance(val, dict) and "fmt" in val:
                        val = val["fmt"]
                    info[field] = val
        return info

    async def _get_full_data_via_worker(self, ticker: str) -> Optional[FullMarketData]:
        """熔断时通过 Worker 代理获取全量数据"""
        if not self._worker_url or not self._worker_key:
            return None
        symbol = self._normalize_ticker(ticker)

        # 并发获取多个端点
        qs_task = self._get_quote_summary_via_worker(symbol)
        rec_task = self._get_recommendations_via_worker(symbol)
        cal_task = self._get_calendar_via_worker(symbol)
        hist_task = self._get_history_df_via_worker(symbol, "1y", "1d")
        news_task = self._get_news_via_worker_raw(symbol)

        qs, rec_data, cal_data, hist_df, news_stream = await asyncio.gather(
            qs_task, rec_task, cal_task, hist_task, news_task,
            return_exceptions=True
        )

        if not qs or isinstance(qs, Exception):
            return None

        info = self._parse_quote_summary_to_info(qs)

        # 补充 analyst 数据
        if rec_data and not isinstance(rec_data, Exception):
            rec_trend = rec_data.get("recommendationTrend", {}).get("trend", [])
            if rec_trend:
                latest = rec_trend[0]
                info["_analyst_buy"] = int(latest.get("strongBuy", 0) or 0) + int(latest.get("buy", 0) or 0)
                info["_analyst_hold"] = int(latest.get("hold", 0) or 0)
                info["_analyst_sell"] = int(latest.get("sell", 0) or 0) + int(latest.get("strongSell", 0) or 0)

        if cal_data and not isinstance(cal_data, Exception):
            cal_events = cal_data.get("calendarEvents", {})
            earn = cal_events.get("earnings", {}).get("earningsDate")
            if earn:
                if isinstance(earn, list) and len(earn) > 0:
                    raw = earn[0].get("raw") or earn[0].get("fmt")
                    info["_earnings_date"] = str(raw)[:10] if raw else None
                else:
                    raw = earn.get("raw") or earn.get("fmt")
                    info["_earnings_date"] = str(raw)[:10] if raw else None

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        previous_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if price is None:
            return None

        change = float(price) - float(previous_close) if previous_close not in (None, 0) else 0.0
        change_percent = (change / float(previous_close) * 100) if previous_close not in (None, 0) else 0.0

        quote = ProviderQuote(
            ticker=ticker.upper(),
            price=float(price),
            change=change,
            change_percent=change_percent,
            name=info.get("shortName") or info.get("longName") or ticker.upper(),
            market_status=self._market_status_from_info(info),
            last_updated=utc_now_naive(),
        )

        indicators = None
        if hist_df is not None and not isinstance(hist_df, Exception) and not hist_df.empty:
            indicators = TechnicalIndicators.calculate_all(hist_df.set_index("Date"))

        fundamental = self._build_fundamental_from_info(info, ticker)

        news = []
        if news_stream and not isinstance(news_stream, Exception):
            news = self._parse_worker_news(news_stream, symbol)

        return FullMarketData(
            quote=quote,
            fundamental=fundamental,
            technical=ProviderTechnical(indicators=indicators) if indicators else None,
            news=news,
        )

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
        """一站式获取全量数据：单次 yf.Ticker 实例，避免重复 .info 请求。
        这是解决 Yahoo Finance 限频的核心优化。
        """
        if self.is_rate_limited():
            logger.debug(f"[YFinance] Circuit breaker active for {ticker}, skipping")
            return None

        symbol = self._normalize_ticker(ticker)

        def fetch_all():
            stock = yf.Ticker(symbol)
            info = self._get_cached_info(symbol, stock)
            if not info:
                return None

            fast_info = dict(getattr(stock, "fast_info", {}) or {})
            price = fast_info.get("lastPrice") or info.get("regularMarketPrice") or info.get("currentPrice")
            previous_close = fast_info.get("previousClose") or info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price is None:
                return None
            change = float(price) - float(previous_close) if previous_close not in (None, 0) else 0.0
            change_percent = (change / float(previous_close) * 100) if previous_close not in (None, 0) else 0.0
            name = info.get("shortName") or info.get("longName") or ticker.upper()
            quote = ProviderQuote(
                ticker=ticker.upper(),
                price=float(price),
                change=change,
                change_percent=change_percent,
                name=name,
                market_status=self._market_status_from_info(info),
                last_updated=utc_now_naive(),
            )

            try:
                history = stock.history(period="1y", interval="1d", auto_adjust=False, actions=False)
                hist_df = self._history_to_dataframe(history)
                indicators = None
                if hist_df is not None and not hist_df.empty:
                    indicators = TechnicalIndicators.calculate_all(hist_df.set_index("Date"))
            except Exception:
                indicators = None

            buy_c = info.get("_analyst_buy")
            hold_c = info.get("_analyst_hold")
            sell_c = info.get("_analyst_sell")
            total_count = None
            if buy_c is not None or hold_c is not None or sell_c is not None:
                total_count = (buy_c or 0) + (hold_c or 0) + (sell_c or 0)

            vix_value = self._get_cached_vix()

            fundamental = ProviderFundamental(
                name=info.get("shortName") or info.get("longName"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=float(info["marketCap"]) if info.get("marketCap") is not None else None,
                pe_ratio=float(info["trailingPE"]) if info.get("trailingPE") is not None else None,
                forward_pe=float(info["forwardPE"]) if info.get("forwardPE") is not None else None,
                eps=float(info["trailingEps"]) if info.get("trailingEps") is not None else None,
                dividend_yield=float(info["dividendYield"]) if info.get("dividendYield") is not None else None,
                beta=float(info["beta"]) if info.get("beta") is not None else None,
                fifty_two_week_high=float(info["fiftyTwoWeekHigh"]) if info.get("fiftyTwoWeekHigh") is not None else None,
                fifty_two_week_low=float(info["fiftyTwoWeekLow"]) if info.get("fiftyTwoWeekLow") is not None else None,
                earnings_date=info.get("_earnings_date"),
                target_price_mean=float(info["targetMeanPrice"]) if info.get("targetMeanPrice") is not None else None,
                analyst_count=int(info["numberOfAnalystOpinions"]) if info.get("numberOfAnalystOpinions") is not None else total_count,
                analyst_buy_count=buy_c,
                analyst_hold_count=hold_c,
                analyst_sell_count=sell_c,
                vix=vix_value,
            )

            news = []
            try:
                raw_items = list(getattr(stock, "news", None) or [])
                seen_links: set[str] = set()
                for index, item in enumerate(raw_items[:10]):
                    content = item.get("content") or {}
                    title = content.get("title") or item.get("title")
                    link = content.get("canonicalUrl", {}).get("url") or content.get("clickThroughUrl", {}).get("url") or item.get("link")
                    publisher = content.get("provider", {}).get("displayName") or item.get("publisher")
                    summary = content.get("summary") or item.get("summary")
                    pub_ts = content.get("pubDate") or item.get("providerPublishTime")
                    if not title or not link or link in seen_links:
                        continue
                    publish_time = utc_now_naive()
                    if pub_ts:
                        try:
                            if isinstance(pub_ts, (int, float)):
                                publish_time = datetime.fromtimestamp(pub_ts)
                            else:
                                publish_time = pd.to_datetime(pub_ts).to_pydatetime().replace(tzinfo=None)
                        except Exception:
                            pass
                    news.append(
                        ProviderNews(
                            id=f"yfinance-{symbol.lower()}-{index}",
                            title=title,
                            publisher=publisher or "Yahoo Finance",
                            link=link,
                            summary=summary,
                            publish_time=publish_time,
                        )
                    )
                    seen_links.add(link)
            except Exception:
                pass

            return FullMarketData(
                quote=quote,
                fundamental=fundamental,
                technical=ProviderTechnical(indicators=indicators) if indicators else None,
                news=news,
            )

        # 重试逻辑：Yahoo 限频时自动退避重试
        max_retries = 3
        base_delay = 3.0
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                result = await self._run_sync(fetch_all)
                if result:
                    logger.info(f"[YFinance] get_full_data completed for {ticker} (single Ticker session, attempt {attempt+1})")
                return result
            except Exception as exc:
                last_exc = exc
                error_msg = str(exc)
                if "Too Many Requests" in error_msg or "rate" in error_msg.lower():
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"YFinance rate limited for {ticker}, retry {attempt+1}/{max_retries} after {delay}s: {exc}")
                    time.sleep(delay)
                else:
                    raise
        logger.warning(f"YFinance get_full_data exhausted all retries for {ticker}: {last_exc}")
        self._activate_rate_limit_cooldown()
        return await self._get_full_data_via_worker(ticker)

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        if self.is_rate_limited():
            # 熔断期间走 Worker 代理
            return await self._get_quote_via_worker(ticker)
        symbol = self._normalize_ticker(ticker)

        try:
            def fetch_quote() -> tuple[dict[str, Any], dict[str, Any]]:
                stock = yf.Ticker(symbol)
                fast_info = getattr(stock, "fast_info", {}) or {}
                info = dict(getattr(stock, "info", {}) or {})
                return dict(fast_info), info

            fast_info, info = await self._run_sync(fetch_quote)
            price = fast_info.get("lastPrice") or info.get("regularMarketPrice") or info.get("currentPrice")
            previous_close = fast_info.get("previousClose") or info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price is None:
                return None

            change = float(price) - float(previous_close) if previous_close not in (None, 0) else 0.0
            change_percent = (change / float(previous_close) * 100) if previous_close not in (None, 0) else 0.0
            name = info.get("shortName") or info.get("longName") or ticker.upper()

            return ProviderQuote(
                ticker=ticker.upper(),
                price=float(price),
                change=change,
                change_percent=change_percent,
                name=name,
                market_status=self._market_status_from_info(info),
                last_updated=utc_now_naive(),
            )
        except Exception as exc:
            logger.warning(f"YFinance get_quote failed for {ticker}: {exc}")
            return await self._get_quote_via_worker(ticker)

    async def _get_quote_via_worker(self, ticker: str) -> Optional[ProviderQuote]:
        """熔断时通过 Worker 代理获取 quote"""
        if not self._worker_url or not self._worker_key:
            return None
        symbol = self._normalize_ticker(ticker)

        v7_data = await self._get_v7_quote_via_worker(symbol)
        if v7_data:
            price = v7_data.get("regularMarketPrice")
            previous_close = v7_data.get("regularMarketPreviousClose")
            name = v7_data.get("shortName") or v7_data.get("longName") or ticker.upper()
            state = v7_data.get("marketState", "REGULAR")
            if price is not None:
                change = float(price) - float(previous_close) if previous_close not in (None, 0) else 0.0
                change_percent = (change / float(previous_close) * 100) if previous_close not in (None, 0) else 0.0
                status_map = {"PRE": MarketStatus.PRE_MARKET, "POST": MarketStatus.AFTER_HOURS, "AFTER_HOURS": MarketStatus.AFTER_HOURS}
                return ProviderQuote(
                    ticker=ticker.upper(),
                    price=float(price),
                    change=change,
                    change_percent=change_percent,
                    name=name,
                    market_status=status_map.get(state, MarketStatus.OPEN),
                    last_updated=utc_now_naive(),
                )

        # Fallback: 尝试 quoteSummary
        qs = await self._get_quote_summary_via_worker(symbol)
        if not qs:
            return None
        info = self._parse_quote_summary_to_info(qs)
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        previous_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if price is None:
            return None
        change = float(price) - float(previous_close) if previous_close not in (None, 0) else 0.0
        change_percent = (change / float(previous_close) * 100) if previous_close not in (None, 0) else 0.0
        return ProviderQuote(
            ticker=ticker.upper(),
            price=float(price),
            change=change,
            change_percent=change_percent,
            name=info.get("shortName") or info.get("longName") or ticker.upper(),
            market_status=self._market_status_from_info(info),
            last_updated=utc_now_naive(),
        )

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        if self.is_rate_limited():
            return await self._get_fundamental_via_worker(ticker)
        symbol = self._normalize_ticker(ticker)
        try:
            def fetch_info() -> dict[str, Any]:
                stock = yf.Ticker(symbol)
                return self._get_cached_info(symbol, stock)

            info = await self._run_sync(fetch_info)
            if not info:
                return await self._get_fundamental_via_worker(ticker)

            return self._build_fundamental_from_info(info, ticker)
        except Exception as exc:
            logger.warning(f"YFinance get_fundamental_data failed for {ticker}: {exc}")
            return await self._get_fundamental_via_worker(ticker)

    def _build_fundamental_from_info(self, info: dict, ticker: str) -> ProviderFundamental:
        """从 info dict 构建 Fundamental 对象（直连和 Worker 共用）"""
        vix_value = self._get_cached_vix()
        buy_c = info.get("_analyst_buy")
        hold_c = info.get("_analyst_hold")
        sell_c = info.get("_analyst_sell")
        total_count = None
        if buy_c is not None or hold_c is not None or sell_c is not None:
            total_count = (buy_c or 0) + (hold_c or 0) + (sell_c or 0)

        return ProviderFundamental(
            name=info.get("shortName") or info.get("longName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=float(info["marketCap"]) if info.get("marketCap") is not None else None,
            pe_ratio=float(info["trailingPE"]) if info.get("trailingPE") is not None else None,
            forward_pe=float(info["forwardPE"]) if info.get("forwardPE") is not None else None,
            eps=float(info["trailingEps"]) if info.get("trailingEps") is not None else None,
            dividend_yield=float(info["dividendYield"]) if info.get("dividendYield") is not None else None,
            beta=float(info["beta"]) if info.get("beta") is not None else None,
            fifty_two_week_high=float(info["fiftyTwoWeekHigh"]) if info.get("fiftyTwoWeekHigh") is not None else None,
            fifty_two_week_low=float(info["fiftyTwoWeekLow"]) if info.get("fiftyTwoWeekLow") is not None else None,
            earnings_date=info.get("_earnings_date"),
            target_price_mean=float(info["targetMeanPrice"]) if info.get("targetMeanPrice") is not None else None,
            analyst_count=int(info["numberOfAnalystOpinions"]) if info.get("numberOfAnalystOpinions") is not None else total_count,
            analyst_buy_count=buy_c,
            analyst_hold_count=hold_c,
            analyst_sell_count=sell_c,
            vix=vix_value,
        )

    async def _get_fundamental_via_worker(self, ticker: str) -> Optional[ProviderFundamental]:
        """熔断时通过 Worker 代理获取 fundamental data"""
        if not self._worker_url or not self._worker_key:
            return None
        symbol = self._normalize_ticker(ticker)

        qs = await self._get_quote_summary_via_worker(symbol)
        if not qs:
            return None
        info = self._parse_quote_summary_to_info(qs)

        # 额外获取 recommendations 和 calendar
        rec_data = await self._get_recommendations_via_worker(symbol)
        cal_data = await self._get_calendar_via_worker(symbol)

        if rec_data:
            rec_trend = rec_data.get("recommendationTrend", {}).get("trend", [])
            if rec_trend:
                latest = rec_trend[0]
                info["_analyst_buy"] = int(latest.get("strongBuy", 0) or 0) + int(latest.get("buy", 0) or 0)
                info["_analyst_hold"] = int(latest.get("hold", 0) or 0)
                info["_analyst_sell"] = int(latest.get("sell", 0) or 0) + int(latest.get("strongSell", 0) or 0)

        if cal_data:
            cal_events = cal_data.get("calendarEvents", {})
            earn = cal_events.get("earnings", {}).get("earningsDate")
            if earn:
                if isinstance(earn, list) and len(earn) > 0:
                    raw = earn[0].get("raw") or earn[0].get("fmt")
                    info["_earnings_date"] = str(raw)[:10] if raw else None
                else:
                    raw = earn.get("raw") or earn.get("fmt")
                    info["_earnings_date"] = str(raw)[:10] if raw else None

        return self._build_fundamental_from_info(info, ticker)

    async def get_historical_data(
        self,
        ticker: str,
        interval: str = "1d",
        period: str = "1mo",
        end_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        # _get_history_df 内部已处理 Worker 代理 fallback，无需在此拦截
        try:
            df = await self._get_history_df(ticker, period=period, interval=interval)
            if df is None or df.empty or len(df) < 2:
                return None

            indicators = TechnicalIndicators.calculate_all(df.set_index("Date"))
            bars = []
            for _, row in df.iterrows():
                bars.append(
                    {
                        "time": row["Date"].strftime("%Y-%m-%d"),
                        "open": float(row.get("Open", 0) or 0),
                        "high": float(row.get("High", 0) or 0),
                        "low": float(row.get("Low", 0) or 0),
                        "close": float(row.get("Close", 0) or 0),
                        "volume": float(row.get("Volume", 0) or 0),
                    }
                )

            return {
                "ticker": ticker.upper(),
                "bars": bars,
                "indicators": indicators,
                "metadata": {
                    "count": len(bars),
                    "source": "yfinance",
                },
            }
        except Exception as exc:
            logger.warning(f"YFinance get_historical_data failed for {ticker}: {exc}")
            return None

    async def get_ohlcv(
        self,
        ticker: str,
        interval: str = "1d",
        period: str = "1y",
        end_date: Optional[str] = None,
    ) -> List[Any]:
        try:
            df = await self._get_history_df(ticker, period=period, interval=interval)
            if df is None or df.empty:
                return []

            calc_df = TechnicalIndicators.add_historical_indicators(df)
            calc_df = calc_df.where(pd.notnull(calc_df), None)
            calc_df["time"] = calc_df["Date"].dt.strftime("%Y-%m-%d")

            return [
                OHLCVItem(
                    time=row["time"],
                    open=float(row.get("Open", 0) or 0),
                    high=float(row.get("High", 0) or 0),
                    low=float(row.get("Low", 0) or 0),
                    close=float(row.get("Close", 0) or 0),
                    volume=float(row.get("Volume", 0) or 0),
                    rsi=row.get("rsi"),
                    macd=row.get("macd"),
                    macd_signal=row.get("macd_signal"),
                    macd_hist=row.get("macd_hist"),
                    bb_upper=row.get("bb_upper"),
                    bb_middle=row.get("bb_middle"),
                    bb_lower=row.get("bb_lower"),
                )
                for row in calc_df.to_dict("records")
            ]
        except Exception as exc:
            logger.warning(f"YFinance get_ohlcv failed for {ticker}: {exc}")
            return []

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        if self.is_rate_limited():
            return await self._get_news_via_worker(ticker)
        symbol = self._normalize_ticker(ticker)
        try:
            def fetch_news() -> list[dict[str, Any]]:
                stock = yf.Ticker(symbol)
                raw_news = getattr(stock, "news", None) or []
                return list(raw_news)

            raw_items = await self._run_sync(fetch_news)
            results = self._parse_news_items(raw_items, symbol)
            return results if results else await self._get_news_via_worker(ticker)
        except Exception as exc:
            logger.warning(f"YFinance get_news failed for {ticker}: {exc}")
            return await self._get_news_via_worker(ticker)

    @staticmethod
    def _parse_news_items(raw_items: list, symbol: str) -> list[ProviderNews]:
        """统一解析新闻列表"""
        results: list[ProviderNews] = []
        seen_links: set[str] = set()
        for index, item in enumerate(raw_items[:10]):
            content = item.get("content") or {}
            title = content.get("title") or item.get("title")
            link = content.get("canonicalUrl", {}).get("url") or content.get("clickThroughUrl", {}).get("url") or item.get("link")
            publisher = content.get("provider", {}).get("displayName") or item.get("publisher")
            summary = content.get("summary") or item.get("summary")
            pub_ts = content.get("pubDate") or item.get("providerPublishTime")

            if not title or not link or link in seen_links:
                continue

            publish_time = utc_now_naive()
            if pub_ts:
                try:
                    if isinstance(pub_ts, (int, float)):
                        publish_time = datetime.fromtimestamp(pub_ts)
                    else:
                        publish_time = pd.to_datetime(pub_ts).to_pydatetime().replace(tzinfo=None)
                except Exception:
                    publish_time = utc_now_naive()

            results.append(
                ProviderNews(
                    id=f"yfinance-{symbol.lower()}-{index}",
                    title=title,
                    publisher=publisher or "Yahoo Finance",
                    link=link,
                    summary=summary,
                    publish_time=publish_time,
                )
            )
            seen_links.add(link)
        return results

    async def _get_news_via_worker(self, ticker: str) -> List[ProviderNews]:
        """熔断时通过 Worker 代理获取新闻"""
        if not self._worker_url or not self._worker_key:
            return []
        symbol = self._normalize_ticker(ticker)

        stream = await self._get_news_via_worker_raw(symbol)
        if not stream:
            return []
        return self._parse_worker_news(stream, symbol)

    async def _get_news_via_worker_raw(self, symbol: str) -> Optional[list]:
        """Worker 新闻原始数据"""
        url = "https://finance.yahoo.com/xhr/ncp?queryRef=latestNews&serviceKey=ncp_fin"
        data = await self._proxy_via_worker(
            url,
            method="POST",
            body={"serviceConfig": {"snippetCount": 10, "s": [symbol]}}
        )
        if not data:
            return None
        return data.get("data", {}).get("content", {}).get("stream", [])

    @staticmethod
    def _parse_worker_news(stream: list, symbol: str) -> list[ProviderNews]:
        """解析 Worker 返回的新闻流"""
        results: list[ProviderNews] = []
        seen_links: set[str] = set()
        for index, item in enumerate(stream[:10]):
            content = item.get("content") or {}
            title = content.get("title") or item.get("title")
            link = content.get("canonicalUrl", {}).get("url") or content.get("clickThroughUrl", {}).get("url") or item.get("link")
            publisher = content.get("provider", {}).get("displayName") or item.get("publisher")
            summary = content.get("summary") or item.get("summary")
            pub_ts = content.get("pubDate") or item.get("providerPublishTime")

            if not title or not link or link in seen_links:
                continue

            publish_time = utc_now_naive()
            if pub_ts:
                try:
                    if isinstance(pub_ts, (int, float)):
                        publish_time = datetime.fromtimestamp(pub_ts)
                    else:
                        publish_time = pd.to_datetime(pub_ts).to_pydatetime().replace(tzinfo=None)
                except Exception:
                    pass

            results.append(
                ProviderNews(
                    id=f"yfinance-worker-{symbol.lower()}-{index}",
                    title=title,
                    publisher=publisher or "Yahoo Finance",
                    link=link,
                    summary=summary,
                    publish_time=publish_time,
                )
            )
            seen_links.add(link)
        return results
