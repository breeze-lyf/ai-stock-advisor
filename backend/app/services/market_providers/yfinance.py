from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from app.schemas.market_data import MarketStatus, OHLCVItem, ProviderFundamental, ProviderNews, ProviderQuote
from app.services.indicators import TechnicalIndicators
from app.services.market_providers.base import MarketDataProvider
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


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
        return await asyncio.to_thread(func, *args, **kwargs)

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

        def fetch_history() -> pd.DataFrame:
            stock = yf.Ticker(symbol)
            return stock.history(period=yf_period, interval=yf_interval, auto_adjust=False, actions=False)

        history = await self._run_sync(fetch_history)
        return self._history_to_dataframe(history)

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
                return dict(getattr(stock, "info", {}) or {})

            info = await self._run_sync(fetch_info)
            if not info:
                return None

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
