from __future__ import annotations

import asyncio
import logging
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
        normalized = (query or "").strip()
        if not normalized:
            return []

        ACCEPTED_QUOTE_TYPES = {"EQUITY", "ETF", "MUTUALFUND", "INDEX", "CURRENCY", "CRYPTOCURRENCY", "FUTURE", "MARKET"}

        try:
            def run_search() -> list[dict[str, Any]]:
                search = yf.Search(
                    normalized,
                    max_results=max(limit, 30),
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

        try:
            history = await self._run_sync(lambda: yf.Ticker(symbol).history(
                period=yf_period, interval=yf_interval, auto_adjust=False, actions=False
            ))
            df = self._history_to_dataframe(history)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[YFinance] Failed to fetch history for {ticker}: {e}")

        return None

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
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
        logger.error(f"YFinance get_full_data exhausted all retries for {ticker}: {last_exc}")
        return None

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
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
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        symbol = self._normalize_ticker(ticker)
        try:
            def fetch_info() -> dict[str, Any]:
                stock = yf.Ticker(symbol)
                return self._get_cached_info(symbol, stock)

            info = await self._run_sync(fetch_info)
            if not info:
                return None

            return self._build_fundamental_from_info(info, ticker)
        except Exception as exc:
            logger.warning(f"YFinance get_fundamental_data failed for {ticker}: {exc}")
            return None

    def _build_fundamental_from_info(self, info: dict, ticker: str) -> ProviderFundamental:
        """从 info dict 构建 Fundamental 对象"""
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

    async def get_historical_data(
        self,
        ticker: str,
        interval: str = "1d",
        period: str = "1mo",
        end_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
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
        symbol = self._normalize_ticker(ticker)
        try:
            def fetch_news() -> list[dict[str, Any]]:
                stock = yf.Ticker(symbol)
                raw_news = getattr(stock, "news", None) or []
                return list(raw_news)

            raw_items = await self._run_sync(fetch_news)
            return self._parse_news_items(raw_items, symbol)
        except Exception as exc:
            logger.warning(f"YFinance get_news failed for {ticker}: {exc}")
            return []

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
