import time
import akshare as ak
import pandas as pd
import logging
import asyncio
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from app.services.market_providers.base import MarketDataProvider
from app.schemas.market_data import (
    ProviderQuote, ProviderFundamental, ProviderNews, MarketStatus
)
from app.services.indicators import TechnicalIndicators

import threading
import requests.utils

# 线程本地变量，用于在 A 股/美股抓取线程中标记是否停用代理 (Thread Local Storage for Proxy Bypassing)
_tls = threading.local()

# 备份原始 requests.utils.get_environ_proxies
_original_get_environ_proxies = requests.utils.get_environ_proxies

def _patched_get_environ_proxies(*args, **kwargs):
    """
    monkey-patch 函数，针对标记了 bypass_proxy 的线程返回空代理。
    国内服务器访问 AkShare (EM/Sina) 必须禁用代理，否则会因代理服务器位于海外而被目标反扒机制拦截。
    """
    if getattr(_tls, 'bypass_proxy', False):
        return {}
    return _original_get_environ_proxies(*args, **kwargs)

# 应用全局 patch
requests.utils.get_environ_proxies = _patched_get_environ_proxies

logger = logging.getLogger(__name__)

class AkShareProvider(MarketDataProvider):
    # 类级内存缓存 (Class-level In-memory Cache)
    _cached_spot_df = None
    _last_spot_update = 0
    _cached_us_spot_df = None
    _last_us_spot_update = 0
    
    _async_lock = None 
    _CACHE_TTL = 60  # 缓存有效期 60 秒

    @classmethod
    def _get_lock(cls):
        if cls._async_lock is None:
            cls._async_lock = asyncio.Lock()
        return cls._async_lock

    async def _run_sync(self, func, *args, **kwargs):
        """
        在线程池中运行同步函数，并强制禁用代理。
        """
        def run_isolated():
            _tls.bypass_proxy = True
            # 双重保险：清除环境变量
            old_http = os.environ.get('HTTP_PROXY')
            old_https = os.environ.get('HTTPS_PROXY')
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
                if var in os.environ: del os.environ[var]
            
            try:
                return func(*args, **kwargs)
            finally:
                _tls.bypass_proxy = False
                if old_http: os.environ['HTTP_PROXY'] = old_http
                if old_https: os.environ['HTTPS_PROXY'] = old_https

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_isolated)

    def _normalize_symbol(self, ticker: str) -> str:
        return ticker.split('.')[0] if '.' in ticker else ticker

    def _is_us_stock(self, ticker: str) -> bool:
        """判定是否为美股（非 6 位纯数字，或包含字母）"""
        return not (ticker.isdigit() and len(ticker) == 6)

    def _get_sina_symbol(self, ticker: str) -> str:
        symbol = self._normalize_symbol(ticker)
        if symbol.startswith(('60', '68', '11')): return f"sh{symbol}"
        if symbol.startswith(('00', '30', '12')): return f"sz{symbol}"
        return symbol

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """获取行情，智能路由 A 股或美股"""
        if self._is_us_stock(ticker):
            return await self._get_us_quote(ticker)
            
        symbol = self._normalize_symbol(ticker)
        try:
            # 个股极速路径 (Hist + Info)
            price, change_percent, name = None, 0.0, None
            try:
                hist_df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
                if hist_df is not None and not hist_df.empty:
                    latest = hist_df.iloc[-1]
                    price = float(latest['收盘'])
                    change_percent = float(latest.get('涨跌幅', 0.0))
            except: pass

            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    name = str(data.get('股票简称', ticker))
                    if price is None and data.get('最新') != '-':
                        price = float(data.get('最新'))
            except: pass

            if price is not None:
                return ProviderQuote(ticker=ticker, price=price, change_percent=change_percent, name=name or ticker, last_updated=datetime.utcnow())

            return None
        except Exception as e:
            logger.error(f"AkShare get_quote error for {ticker}: {e}")
            return None

    async def _get_us_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """专用于获取美股行情的内部方法"""
        try:
            # 极速路径：直接从个股历史数据中提取最近一天的收盘价
            hist_df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
            if hist_df is not None and not hist_df.empty:
                latest = hist_df.iloc[-1]
                # 计算最后两天的涨跌幅
                prev_close = hist_df.iloc[-2]['close'] if len(hist_df) > 1 else latest['close']
                change_pct = (latest['close'] - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
                return ProviderQuote(
                    ticker=ticker,
                    price=float(latest['close']),
                    change_percent=change_pct,
                    name=ticker, # 无法从历史接口拿名称，系统稍后会用数据库里的 name 或兜底 name
                    market_status=MarketStatus.OPEN,
                    last_updated=datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"AkShare _get_us_quote error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        if self._is_us_stock(ticker):
            return await self._get_us_fundamental(ticker)
        
        symbol = self._normalize_symbol(ticker)
        try:
            name, sector, mc, pe, eps = None, None, None, None, None
            # 优先从缓存拿 PE/市值
            if AkShareProvider._cached_spot_df is not None:
                row = AkShareProvider._cached_spot_df[AkShareProvider._cached_spot_df['代码'] == symbol]
                if not row.empty:
                    target = row.iloc[0]
                    name, pe, mc = str(target.get('名称')), float(target.get('市盈率-动态', 0)), float(target.get('总市值', 0))
                    price = float(target.get('最新价', 0))
                    if pe > 0: eps = price / pe

            # info 补全行业
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    sector = data.get('行业')
                    if not mc: mc = float(data.get('总市值', 0))
                    if not name: name = data.get('股票简称')
            except: pass

            return ProviderFundamental(name=name, sector=sector, industry=sector, market_cap=mc, pe_ratio=pe, eps=eps)
        except Exception as e:
            logger.error(f"AkShare get_fundamental_data error for {ticker}: {e}")
            return None

    async def _get_us_fundamental(self, ticker: str) -> Optional[ProviderFundamental]:
        """美股基础面增强"""
        try:
            name, pe, mc = ticker, None, None
            if AkShareProvider._cached_us_spot_df is not None:
                row = AkShareProvider._cached_us_spot_df[AkShareProvider._cached_us_spot_df['代码'] == ticker]
                if not row.empty:
                    target = row.iloc[0]
                    name, pe, mc = str(target.get('名称', ticker)), float(target.get('市盈率', 0)), float(target.get('总市值', 0))
            return ProviderFundamental(name=name, market_cap=mc, pe_ratio=pe)
        except: return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Dict[str, Any]]:
        try:
            if self._is_us_stock(ticker):
                df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                if df is not None and not df.empty:
                    df = df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
            else:
                symbol = self._normalize_symbol(ticker)
                df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
                if df is not None and not df.empty:
                    df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
            
            if df is None or df.empty: return None
            return TechnicalIndicators.calculate_all(df)
        except Exception as e:
            logger.error(f"AkShare get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        if self._is_us_stock(ticker): return [] # 美股新闻建议由 TavilyProvider 处理 (RAG 更强)
        try:
            symbol = self._normalize_symbol(ticker)
            news_df = await self._run_sync(ak.stock_news_em, symbol=symbol)
            import hashlib
            results = []
            for _, row in news_df.head(10).iterrows():
                link = row['新闻链接']
                unique_id = hashlib.md5(link.encode()).hexdigest()
                results.append(ProviderNews(id=f"ak-{unique_id}", title=row['新闻标题'], publisher=row.get('文章来源', '东财'), link=link, publish_time=pd.to_datetime(row['发布时间'])))
            return results
        except: return []

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> List[Any]:
        try:
            if self._is_us_stock(ticker):
                df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                if df is not None and not df.empty:
                    df = df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
            else:
                symbol = self._normalize_symbol(ticker)
                df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
                if df is not None and not df.empty:
                    df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})

            if df is None or df.empty: return []
            
            df['Date'] = pd.to_datetime(df['Date'])
            calc_df = TechnicalIndicators.add_historical_indicators(df)
            
            from app.schemas.market_data import OHLCVItem
            data = []
            for _, row in calc_df.iterrows():
                dt = row['Date']
                data.append(OHLCVItem(
                    time=dt.strftime('%Y-%m-%d'), open=float(row['Open']), high=float(row['High']), 
                    low=float(row['Low']), close=float(row['Close']), volume=float(row.get('Volume', 0)),
                    rsi=float(row['rsi']) if 'rsi' in row and not pd.isna(row['rsi']) else None,
                    macd=float(row['macd']) if 'macd' in row and not pd.isna(row['macd']) else None,
                    macd_signal=float(row['macd_signal']) if 'macd_signal' in row and not pd.isna(row['macd_signal']) else None,
                    macd_hist=float(row['macd_hist']) if 'macd_hist' in row and not pd.isna(row['macd_hist']) else None,
                    bb_upper=float(row['bb_upper']) if 'bb_upper' in row and not pd.isna(row['bb_upper']) else None,
                    bb_middle=float(row['bb_middle']) if 'bb_middle' in row and not pd.isna(row['bb_middle']) else None,
                    bb_lower=float(row['bb_lower']) if 'bb_lower' in row and not pd.isna(row['bb_lower']) else None,
                ))
            return data
        except Exception as e:
            logger.error(f"AkShare get_ohlcv error for {ticker}: {e}")
            return []
