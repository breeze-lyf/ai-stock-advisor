import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider
from app.services.indicators import TechnicalIndicators
from app.schemas.market_data import (
    ProviderQuote, ProviderFundamental, ProviderNews, MarketStatus, OHLCVItem
)
import pandas as pd

logger = logging.getLogger(__name__)

class AlphaVantageProvider(MarketDataProvider):
    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_API_KEY

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        if not self.api_key:
            return None
            
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            quote = data.get("Global Quote")
            if quote:
                return ProviderQuote(
                    ticker=ticker,
                    price=float(quote.get("05. price", 0)),
                    change_percent=float(quote.get("10. change percent", "0%").replace("%", "")),
                    name=ticker,
                    market_status=MarketStatus.OPEN,
                    last_updated=datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"Alpha Vantage get_quote error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        if not self.api_key:
            return None
            
        try:
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if not data or "Symbol" not in data:
                return None
                
            return ProviderFundamental(
                sector=data.get("Sector"),
                industry=data.get("Industry"),
                market_cap=float(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else None,
                pe_ratio=float(data.get("TrailingPE", 0)) if data.get("TrailingPE") != "None" else None,
                forward_pe=float(data.get("ForwardPE", 0)) if data.get("ForwardPE") != "None" else None,
                eps=float(data.get("DilutedEPSTTM", 0)) if data.get("DilutedEPSTTM") != "None" else None,
                dividend_yield=float(data.get("DividendYield", 0)) if data.get("DividendYield") else None,
                beta=float(data.get("Beta", 0)) if data.get("Beta") else None,
                fifty_two_week_high=float(data.get("52WeekHigh", 0)) if data.get("52WeekHigh") else None,
                fifty_two_week_low=float(data.get("52WeekLow", 0)) if data.get("52WeekLow") else None
            )
        except Exception as e:
            logger.error(f"Alpha Vantage get_fundamental_data error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Any]:
        return None

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> List[Any]:
        if not self.api_key:
            return []

        if interval != "1d":
            # AlphaVantage 这里仅实现日线，其他粒度回退给其他 provider
            return []

        try:
            url = (
                "https://www.alphavantage.co/query"
                f"?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=compact&apikey={self.api_key}"
            )
            response = requests.get(url, timeout=20)
            data = response.json()
            series = data.get("Time Series (Daily)")
            if not series:
                return []

            rows = []
            for day, v in series.items():
                rows.append(
                    {
                        "Date": pd.to_datetime(day, errors="coerce"),
                        "Open": float(v.get("1. open", 0) or 0),
                        "High": float(v.get("2. high", 0) or 0),
                        "Low": float(v.get("3. low", 0) or 0),
                        "Close": float(v.get("4. close", 0) or 0),
                        "Volume": float(v.get("5. volume", 0) or 0),
                    }
                )

            if not rows:
                return []

            df = pd.DataFrame(rows).dropna(subset=["Date"]).sort_values("Date")
            if df.empty:
                return []

            now = datetime.now()
            if period == "1mo":
                start_date = now - pd.Timedelta(days=30)
            elif period == "3mo":
                start_date = now - pd.Timedelta(days=90)
            elif period == "6mo":
                start_date = now - pd.Timedelta(days=180)
            elif period == "1y":
                start_date = now - pd.Timedelta(days=365)
            elif period == "5y":
                start_date = now - pd.Timedelta(days=365 * 5)
            else:
                start_date = None

            if start_date is not None:
                df = df[df["Date"] >= start_date]

            if df.empty:
                return []

            df = TechnicalIndicators.add_historical_indicators(df)
            df = df.where(pd.notnull(df), None)

            result: List[OHLCVItem] = []
            for _, row in df.iterrows():
                result.append(
                    OHLCVItem(
                        time=row["Date"].strftime("%Y-%m-%d"),
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
                )

            return result
        except Exception as e:
            logger.error(f"Alpha Vantage get_ohlcv error for {ticker}: {e}")
            return []

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        return []
