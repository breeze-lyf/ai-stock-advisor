from __future__ import annotations

import asyncio
import logging
import httpx
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from app.schemas.market_data import MarketStatus, OHLCVItem, ProviderFundamental, ProviderNews, ProviderQuote
from app.services.indicators import TechnicalIndicators
from app.services.market_providers.base import MarketDataProvider
from app.utils.time import utc_now_naive
from app.core.config import settings

logger = logging.getLogger(__name__)

# 代理环境变量列表
_PROXY_ENV_VARS = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'NO_PROXY']


def _disable_proxy_env():
    """临时禁用代理环境变量，返回原始值"""
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
    # 初始为 False（默认直连），当直连失败时设置为 True
    _use_worker_proxy: bool = False

    @classmethod
    def get_proxy_status(cls) -> bool:
        """获取当前代理状态"""
        return cls._use_worker_proxy

    @classmethod
    def reset_proxy_flag(cls) -> None:
        """重置代理标志，恢复直连模式"""
        cls._use_worker_proxy = False
        logger.info("[YFinance] Proxy flag reset, resuming direct connection")

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

    async def search_instruments(self, query: str, limit: int = 8) -> list[dict[str, str]]:
        normalized = (query or "").strip()
        if not normalized:
            return []

        try:
            def run_search() -> list[dict[str, Any]]:
                search = yf.Search(
                    normalized,
                    max_results=limit,
                    news_count=0,
                    lists_count=0,
                    recommended=limit,
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
                if quote_type and quote_type not in {"EQUITY", "ETF", "MUTUALFUND"}:
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
            # 通过 Worker 代理请求
            worker_request_url = f"{self._worker_url.rstrip('/')}/?url={httpx.URL(yahoo_url)}"

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    worker_request_url,
                    headers={"X-Proxy-Key": self._worker_key},
                    follow_redirects=True,
                )

                if response.status_code != 200:
                    logger.warning(f"[Worker] HTTP {response.status_code} for {symbol}")
                    return None

                data = response.json()

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

        except httpx.TimeoutException:
            logger.warning(f"[Worker] Timeout for {symbol}")
            return None
        except Exception as e:
            logger.warning(f"[Worker] Error for {symbol}: {e}")
            return None

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        symbol = self._normalize_ticker(ticker)

        try:
            def fetch_quote() -> tuple[dict[str, Any], dict[str, Any]]:
                stock = yf.Ticker(symbol)
                fast_info = getattr(stock, "fast_info", {}) or {}
                info = getattr(stock, "info", {}) or {}
                return dict(fast_info), dict(info)

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
                info = dict(getattr(stock, "info", {}) or {})

                # --- 财报日期 (from calendar) ---
                try:
                    cal = stock.calendar
                    if cal is not None and isinstance(cal, dict):
                        earn = cal.get("Earnings Date")
                        if earn is not None:
                            # Can be a list of dates or a single date
                            if isinstance(earn, list) and len(earn) > 0:
                                info["_earnings_date"] = str(earn[0])[:10]
                            else:
                                info["_earnings_date"] = str(earn)[:10]
                except Exception:
                    pass

                # --- 分析师推荐汇总 (from recommendations_summary) ---
                try:
                    rec = stock.recommendations_summary
                    if rec is not None and hasattr(rec, "itertuples") and len(rec) > 0:
                        latest = rec.iloc[0]
                        info["_analyst_buy"] = int(getattr(latest, "strongBuy", 0) or 0) + int(getattr(latest, "buy", 0) or 0)
                        info["_analyst_hold"] = int(getattr(latest, "hold", 0) or 0)
                        info["_analyst_sell"] = int(getattr(latest, "sell", 0) or 0) + int(getattr(latest, "strongSell", 0) or 0)
                except Exception:
                    pass

                return info

            info = await self._run_sync(fetch_info)
            if not info:
                return None

            # --- VIX (fetch separately, only once per process in memory is fine) ---
            vix_value: Optional[float] = None
            try:
                def fetch_vix() -> Optional[float]:
                    vix_info = dict(getattr(yf.Ticker("^VIX"), "info", {}) or {})
                    price = vix_info.get("regularMarketPrice") or vix_info.get("previousClose")
                    return float(price) if price is not None else None
                vix_value = await self._run_sync(fetch_vix)
            except Exception:
                pass

            # --- Analyst counts ---
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
        except Exception as exc:
            logger.warning(f"YFinance get_fundamental_data failed for {ticker}: {exc}")
            return None

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
        except Exception as exc:
            logger.warning(f"YFinance get_news failed for {ticker}: {exc}")
            return []
