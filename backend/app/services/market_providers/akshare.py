import akshare as ak
import pandas as pd
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.market_providers.base import MarketDataProvider
from app.schemas.market_data import (
    ProviderQuote, ProviderFundamental, ProviderNews, MarketStatus
)
from app.services.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

class AkShareProvider(MarketDataProvider):
    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """
        Supports tickers like 600519 (SH) or 000858 (SZ).
        """
        try:
            symbol = ticker.split('.')[0] if '.' in ticker else ticker
            
            # Try spot_em first (full market data)
            df = None
            try:
                # Eastmoney spot
                df = await self._run_sync(ak.stock_zh_a_spot_em)
                if df is not None and not df.empty and '代码' in df.columns:
                    row = df[df['代码'] == symbol]
                    if not row.empty:
                        return ProviderQuote(
                            ticker=ticker,
                            price=float(row.iloc[0]['最新价']),
                            change=float(row.iloc[0]['涨跌额']),
                            change_percent=float(row.iloc[0]['涨跌幅']),
                            name=str(row.iloc[0]['名称']),
                            market_status=MarketStatus.OPEN,
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.warning(f"AkShare spot_em failed for {ticker}: {e}")

            # Fallback 1: Sina spot
            try:
                df = await self._run_sync(ak.stock_zh_a_spot)
                if df is not None and not df.empty and '代码' in df.columns:
                    # Sina '代码' might be sh600519
                    row = df[df['代码'].str.contains(symbol)]
                    if not row.empty:
                        return ProviderQuote(
                            ticker=ticker,
                            price=float(row.iloc[0]['最新价']),
                            change=float(row.iloc[0]['涨跌额']),
                            change_percent=float(row.iloc[0]['涨跌幅']),
                            name=str(row.iloc[0]['名称']),
                            market_status=MarketStatus.OPEN,
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.warning(f"AkShare Sina spot failed for {ticker}: {e}")

            # Fallback 2: Individual Info (Most reliable as it's a single request)
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                if '最新' in data:
                    return ProviderQuote(
                        ticker=ticker,
                        price=float(data['最新']),
                        change_percent=0.0, # Not easily available here
                        name=data.get('股票简称', ticker),
                        market_status=MarketStatus.OPEN,
                        last_updated=datetime.utcnow()
                    )
            except Exception as e:
                logger.warning(f"AkShare individual_info fallback failed for {ticker}: {e}")

            return None
        except Exception as e:
            logger.error(f"AkShare get_quote catastrophic error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        try:
            symbol = ticker.split('.')[0] if '.' in ticker else ticker
            info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
            
            # Map AkShare EM info to standardized fundamental
            # Columns are 'item' and 'value'
            data = {}
            for _, row in info_df.iterrows():
                data[row['item']] = row['value']
            
            return ProviderFundamental(
                sector=data.get('行业'),
                market_cap=float(data.get('总市值', 0)) if data.get('总市值') else None,
                # EM simplified info might not have PE directly in this table
                pe_ratio=None, 
                industry=data.get('行业'),
            )
        except Exception as e:
            logger.error(f"AkShare get_fundamental_data error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Dict[str, Any]]:
        try:
            symbol = ticker.split('.')[0] if '.' in ticker else ticker
            df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
            
            if df.empty:
                return None
            
            df = df.rename(columns={
                '日期': 'Date',
                '开盘': 'Open',
                '收盘': 'Close',
                '最高': 'High',
                '最低': 'Low',
                '成交量': 'Volume'
            })
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            return TechnicalIndicators.calculate_all(df)
        except Exception as e:
            logger.error(f"AkShare get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        try:
            symbol = ticker.split('.')[0] if '.' in ticker else ticker
            news_df = await self._run_sync(ak.stock_news_em, symbol=symbol)
            
            results = []
            for _, row in news_df.head(10).iterrows():
                results.append(ProviderNews(
                    id=str(hash(row['新闻标题'])),
                    title=row['新闻标题'],
                    publisher=row.get('文章来源', row.get('新闻来源', 'Unknown')),
                    link=row['新闻链接'],
                    publish_time=pd.to_datetime(row['发布时间'])
                ))
            return results
        except Exception as e:
            logger.error(f"AkShare get_news error for {ticker}: {e}")
            return []
