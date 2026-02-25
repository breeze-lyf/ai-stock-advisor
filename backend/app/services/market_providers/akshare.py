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
        
        # 使用全局锁防止底层 V8 引擎并发初始化崩溃 (PyMiniRacer)
        async with self._get_lock():
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
            # 兼容性逻辑：判断是否为指数 (Index)
            is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI"]
            hist_df = None
            
            if is_index:
                # 指数路径：新浪接口
                sina_symbol = ticker if ticker.startswith('.') else f".{ticker}"
                if sina_symbol == ".SPX": sina_symbol = ".INX"
                try:
                    hist_df = await self._run_sync(ak.index_us_stock_sina, symbol=sina_symbol)
                except: pass
            
            if hist_df is None or hist_df.empty:
                # 极速路径：直接从个股历史数据中提取最近一天的收盘价
                try:
                    hist_df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                except: pass
            
            # 我们在此处直接使用 httpx 调用 Yahoo 极速底层 API，耗时 < 0.2 秒
            live_price = None
            try:
                import httpx
                async with httpx.AsyncClient(timeout=3.0) as client:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    # Yahoo 使用原始 ticker
                    res = await client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d", headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                        live_price = meta.get("regularMarketPrice")
            except Exception as e:
                logger.warning(f"Failed to fetch live US price from Yahoo for {ticker}: {e}")
                
            if hist_df is not None and not hist_df.empty:
                latest = hist_df.iloc[-1]
                # 计算最后两天的涨跌幅 (EMA接口不同，新浪接口列名是 close，EM是个股接口)
                prev_close = hist_df.iloc[-2]['close'] if len(hist_df) > 1 else latest['close']
                
                current_price = float(live_price) if live_price else float(latest['close'])
                change_pct = float((current_price - float(prev_close)) / float(prev_close) * 100 if prev_close > 0 else 0.0)
                
                return ProviderQuote(
                    ticker=ticker,
                    price=current_price,
                    change_percent=change_pct,
                    name=ticker, 
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
            df = None
            if self._is_us_stock(ticker):
                # 兼容性逻辑：判断是否为指数 (Index)
                is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI"]
                if is_index:
                    sina_symbol = ticker if ticker.startswith('.') else f".{ticker}"
                    if sina_symbol == ".SPX": sina_symbol = ".INX"
                    try:
                        df = await self._run_sync(ak.index_us_stock_sina, symbol=sina_symbol)
                    except: pass

                if df is None or df.empty:
                    try:
                        df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                    except: pass
                
                if df is not None and not df.empty:
                    # 统一列名：新浪接口返回 date, open, high, low, close, volume
                    # 个股接口返回相同，但列名大小写可能不同
                    col_map = {c.lower(): c.capitalize() for c in df.columns}
                    if 'date' in col_map: col_map['date'] = 'Date'
                    df = df.rename(columns=col_map)
            else:
                symbol = self._normalize_symbol(ticker)
                df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
                if df is not None and not df.empty:
                    df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})

            if df is None or df.empty: return []
            
            df['Date'] = pd.to_datetime(df['Date'])
            calc_df = TechnicalIndicators.add_historical_indicators(df)
            
            # 优化 1: 截断历史数据 (保留指标前提下)
            from datetime import datetime, timedelta
            now = datetime.now()
            if period == "1mo": start_date = now - timedelta(days=30)
            elif period == "3mo": start_date = now - timedelta(days=90)
            elif period == "6mo": start_date = now - timedelta(days=180)
            elif period == "1y": start_date = now - timedelta(days=365)
            elif period == "5y": start_date = now - timedelta(days=365*5)
            else: start_date = None
            
            if start_date:
                calc_df = calc_df[calc_df['Date'] >= start_date]

            # 优化 2: 向量化抛弃 iterrows
            calc_df = calc_df.where(pd.notnull(calc_df), None)
            calc_df['time'] = calc_df['Date'].dt.strftime('%Y-%m-%d')
            records = calc_df.to_dict('records')
            
            from app.schemas.market_data import OHLCVItem
            data = []
            for row in records:
                data.append(OHLCVItem(
                    time=row['time'], 
                    open=float(row.get('Open', 0) or 0), 
                    high=float(row.get('High', 0) or 0), 
                    low=float(row.get('Low', 0) or 0), 
                    close=float(row.get('Close', 0) or 0), 
                    volume=float(row.get('Volume', 0) or 0),
                    rsi=row.get('rsi'),
                    macd=row.get('macd'),
                    macd_signal=row.get('macd_signal'),
                    macd_hist=row.get('macd_hist'),
                    bb_upper=row.get('bb_upper'),
                    bb_middle=row.get('bb_middle'),
                    bb_lower=row.get('bb_lower'),
                ))
            return data
        except Exception as e:
            logger.error(f"AkShare get_ohlcv error for {ticker}: {e}")
            return []
