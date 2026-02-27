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
import urllib.request
import urllib3
import urllib3.util.proxy
import requests.sessions

# 线程本地变量，用于在 A 股/美股抓取线程中标记是否停用代理
_tls = threading.local()

# 备份原始逻辑
_original_get_environ_proxies = requests.utils.get_environ_proxies
_original_urllib_getproxies = urllib.request.getproxies
_original_PoolManager_request = urllib3.poolmanager.PoolManager.request
_original_proxy_from_url = urllib3.proxy_from_url
_original_connection_requires_http_tunnel = urllib3.util.proxy.connection_requires_http_tunnel
_original_merge_environment_settings = requests.sessions.Session.merge_environment_settings

def _patched_get_environ_proxies(*args, **kwargs):
    if getattr(_tls, 'bypass_proxy', False): return {}
    return _original_get_environ_proxies(*args, **kwargs)

def _patched_urllib_getproxies():
    if getattr(_tls, 'bypass_proxy', False): return {}
    return _original_urllib_getproxies()

def _patched_PoolManager_request(self, method, url, *args, **kwargs):
    if getattr(_tls, 'bypass_proxy', False):
        kwargs.pop('proxy_url', None)
    return _original_PoolManager_request(self, method, url, *args, **kwargs)

def _patched_proxy_from_url(url, **kw):
    if getattr(_tls, 'bypass_proxy', False): return urllib3.PoolManager(**kw)
    return _original_proxy_from_url(url, **kw)

def _patched_connection_requires_http_tunnel(*args, **kwargs):
    """彻底阻断 HTTPS 隧道的建立"""
    if getattr(_tls, 'bypass_proxy', False): return False
    return _original_connection_requires_http_tunnel(*args, **kwargs)

def _patched_merge_environment_settings(self, url, proxies, *args, **kwargs):
    """拦截 requests.Session 合并环境代理的最后一步"""
    settings = _original_merge_environment_settings(self, url, proxies, *args, **kwargs)
    if getattr(_tls, 'bypass_proxy', False):
        settings['proxies'] = {}
    return settings

# 应用全局劫持
requests.utils.get_environ_proxies = _patched_get_environ_proxies
urllib.request.getproxies = _patched_urllib_getproxies
urllib3.poolmanager.PoolManager.request = _patched_PoolManager_request
urllib3.proxy_from_url = _patched_proxy_from_url
urllib3.poolmanager.proxy_from_url = _patched_proxy_from_url
urllib3.util.proxy.connection_requires_http_tunnel = _patched_connection_requires_http_tunnel
requests.sessions.Session.merge_environment_settings = _patched_merge_environment_settings
requests.Session.merge_environment_settings = _patched_merge_environment_settings

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
    def _get_semaphore(cls):
        if cls._async_lock is None:
            # 使用信号量允许多个协程同时进行 IO 任务，但限制总数防止资源耗尽
            cls._async_lock = asyncio.Semaphore(5)
        return cls._async_lock

    @classmethod
    async def _update_spot_cache(cls):
        """更新 A 股全量实时行情缓存"""
        async with cls._get_semaphore():
            now = time.time()
            if cls._cached_spot_df is not None and (now - cls._last_spot_update) < cls._CACHE_TTL:
                return

            try:
                # 在线程池中执行，避免阻塞事件循环
                def fetch():
                    # 临时禁用代理
                    _tls.bypass_proxy = True
                    env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'NO_PROXY']
                    old_vals = {var: os.environ.get(var) for var in env_vars}
                    for var in env_vars: os.environ.pop(var, None)
                    
                    try:
                        with requests.Session() as s:
                            s.trust_env = False
                            return ak.stock_zh_a_spot_em()
                    finally:
                        _tls.bypass_proxy = False
                        for var, val in old_vals.items():
                            if val is not None: os.environ[var] = val

                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, fetch)
                
                if df is not None and not df.empty:
                    cls._cached_spot_df = df
                    cls._last_spot_update = now
                    logger.info(f"AkShare spot cache updated: {len(df)} stocks")
            except Exception as e:
                logger.error(f"Failed to update AkShare spot cache: {e}")

    async def _run_sync(self, func, *args, **kwargs):
        """
        在线程池中运行同步函数，强制直连。
        """
        def run_isolated():
            _tls.bypass_proxy = True
            # 直接、彻底清理环境变量
            env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'NO_PROXY']
            old_vals = {var: os.environ.get(var) for var in env_vars}
            for var in env_vars: os.environ.pop(var, None)
            
            try:
                # 显式创建禁用环境配置的 Session
                with requests.Session() as s:
                    s.trust_env = False
                    if func == requests.get: return s.get(*args, **kwargs)
                    if func == requests.post: return s.post(*args, **kwargs)
                    return func(*args, **kwargs)
            finally:
                _tls.bypass_proxy = False
                # 还原环境
                for var, val in old_vals.items():
                    if val is not None: os.environ[var] = val

        loop = asyncio.get_event_loop()
        async with self._get_semaphore():
            return await loop.run_in_executor(None, run_isolated)

    def _normalize_symbol(self, ticker: str) -> str:
        # yfinance 风格代码转换: 002050.SZ -> 002050
        return ticker.split('.')[0] if '.' in ticker else ticker

    def _is_us_stock(self, ticker: str) -> bool:
        """判定是否为美股（非 6 位纯数字，或包含字母）"""
        # 如果包含 .SS 或 .SZ 则是 A 股
        if any(suffix in ticker.upper() for suffix in ['.SS', '.SZ']):
            return False
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
            # 1. 尝试从全量实时缓存获取 (速度最快)
            await self._update_spot_cache()
            if AkShareProvider._cached_spot_df is not None:
                df = AkShareProvider._cached_spot_df
                row = df[df['代码'] == symbol]
                if not row.empty:
                    target = row.iloc[0]
                    return ProviderQuote(
                        ticker=ticker,
                        price=float(target.get('最新价', 0)),
                        change_percent=float(target.get('涨跌幅', 0)),
                        name=str(target.get('名称', ticker)),
                        last_updated=datetime.utcnow()
                    )

            # 2. 兜底路径 A：Sina 实时行情 (通常比 EM 稳健)
            try:
                sina_symbol = self._get_sina_symbol(symbol)
                # 使用 stock_zh_a_spot 而不是 stock_zh_a_spot_em
                sina_df = await self._run_sync(ak.stock_zh_a_spot, symbol=sina_symbol)
                if sina_df is not None and not sina_df.empty:
                    target = sina_df.iloc[0]
                    return ProviderQuote(
                        ticker=ticker,
                        price=float(target.get('now', 0)),
                        change_percent=0.0, # Sina spot 不带涨跌幅，需计算或忽略
                        name=str(target.get('name', ticker)),
                        last_updated=datetime.utcnow()
                    )
            except: pass

            # 3. 兜底路径 B：直接请求 East Money API (绕过 AkShare 封装)
            try:
                # 0: sz, 1: sh
                mkt = 1 if symbol.startswith(('60', '68')) else 0
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={mkt}.{symbol}&fields=f43,f170,f58"
                def direct_fetch():
                    _tls.bypass_proxy = True
                    # 环境级禁用
                    old_proxies = {var: os.environ.get(var) for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']}
                    for var in old_proxies:
                        if var in os.environ: del os.environ[var]
                    try:
                        # 显式传递空代理参数，彻底杜绝继承
                        resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"}, proxies={'http': None, 'https': None})
                        return resp.json() if resp.status_code == 200 else None
                    finally:
                        _tls.bypass_proxy = False
                        for var, val in old_proxies.items():
                            if val: os.environ[var] = val
                
                res_json = await loop.run_in_executor(None, direct_fetch)
                if res_json and "data" in res_json and res_json["data"]:
                    d = res_json["data"]
                    return ProviderQuote(
                        ticker=ticker,
                        price=float(d.get('f43', 0) / 100), # 价格通常放大了100倍
                        change_percent=float(d.get('f170', 0) / 100),
                        name=str(d.get('f58', ticker)),
                        last_updated=datetime.utcnow()
                    )
            except: pass

            # 4. 兜底路径 C：EM 单项请求 (AkShare 原生)
            price, change_percent, name = None, 0.0, None
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    name = str(data.get('股票简称', ticker))
                    if data.get('最新') != '-':
                        price = float(data.get('最新'))
            except: pass

            if price is not None:
                return ProviderQuote(ticker=ticker, price=price, change_percent=change_percent, name=name or ticker, last_updated=datetime.utcnow())

            return None
        except Exception as e:
            logger.error(f"AkShare get_quote error for {ticker}: {e}")
            return None

    async def _get_us_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """专用于获取美股行情的内部方法，包含国内直连回退机制"""
        try:
            # 兼容性逻辑：判断是否为指数 (Index)
            is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI"]
            
            # --- 极速路径 1：直接从 Yahoo 底层 API 获取 (通常需要代理) ---
            live_price = None
            try:
                import httpx
                # 只有在可能访问雅虎时才使用 3s 短超时
                async with httpx.AsyncClient(timeout=3.0) as client:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    # Yahoo 使用原始 ticker，注意：这会读取系统 HTTP_PROXY
                    res = await client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d", headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                        live_price = meta.get("regularMarketPrice")
            except Exception as e:
                logger.warning(f"Failed to fetch live US price from Yahoo for {ticker} (likely network/proxy issue): {e}")

            if live_price:
                return ProviderQuote(
                    ticker=ticker,
                    price=float(live_price),
                    change_percent=0.0, # 极速报价暂不计算涨跌幅
                    name=ticker, 
                    market_status=MarketStatus.OPEN,
                    last_updated=datetime.utcnow()
                )

            # --- 回退路径 2：AkShare A 股/美股实时快照缓存 (国内镜像源) ---
            # 如果雅虎挂了（通常是因为没代理），我们使用 AkShare 的美股实时行情
            try:
                now = time.time()
                # 检查缓存是否存在且未过期
                if AkShareProvider._cached_us_spot_df is None or (now - AkShareProvider._last_us_spot_update) > AkShareProvider._CACHE_TTL:
                    async with self._get_semaphore():
                        # 东财美股实时行情
                        us_df = await self._run_sync(ak.stock_us_spot_em)
                        if us_df is not None and not us_df.empty:
                            AkShareProvider._cached_us_spot_df = us_df
                            AkShareProvider._last_us_spot_update = now
                
                if AkShareProvider._cached_us_spot_df is not None:
                    df = AkShareProvider._cached_us_spot_df
                    # EM 代码带后缀，如 AAPL.O；这里处理包含匹配
                    row = df[df['代码'].str.contains(ticker, na=False)]
                    if not row.empty:
                        target = row.iloc[0]
                        return ProviderQuote(
                            ticker=ticker,
                            price=float(target.get('最新价', 0)),
                            change_percent=float(target.get('涨跌幅', 0)),
                            name=str(target.get('名称', ticker)),
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.error(f"AkShare US spot fallback failed for {ticker}: {e}")

            # --- 最终兜底：拉取历史数据取最后一条 ---
            hist_df = None
            if is_index:
                sina_symbol = ticker if ticker.startswith('.') else f".{ticker}"
                if sina_symbol == ".SPX": sina_symbol = ".INX"
                try:
                    hist_df = await self._run_sync(ak.index_us_stock_sina, symbol=sina_symbol)
                except: pass
            
            if hist_df is None or hist_df.empty:
                try:
                    hist_df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                except: pass
                
            if hist_df is not None and not hist_df.empty:
                latest = hist_df.iloc[-1]
                return ProviderQuote(
                    ticker=ticker,
                    price=float(latest['close']),
                    change_percent=0.0,
                    name=ticker, 
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
            await self._update_spot_cache()
            if AkShareProvider._cached_spot_df is not None:
                df = AkShareProvider._cached_spot_df
                row = df[df['代码'] == symbol]
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
