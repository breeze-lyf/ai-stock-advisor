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
        """
        代码归一化: 002050.SZ -> 002050
        注意: 对于美股 (如 BRK.B)，我们要保留点号，因为腾讯接口支持带点的原貌。
        """
        if not ticker: return ticker
        # 如果是 6 位数字开头且带点，判定为 A 股后缀，进行切分
        if ticker[:6].isdigit() and '.' in ticker:
            return ticker.split('.')[0]
        return ticker

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

    def _map_us_sina_ticker(self, ticker: str) -> str:
        """
        美股特殊代码映射 (Sina 命名习惯):
        BRK.B -> brkb
        BF.B -> bfb
        """
        t = ticker.lower()
        mapping = {
            "brk.b": "brkb",
            "brk-b": "brkb",
            "bf.b": "bfb",
            "bf-b": "bfb"
        }
        return mapping.get(t, t)

    async def _get_tencent_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """从腾讯行情接口获取实时报价 (极速、高可用 & 支持基本面提取)"""
        symbol = self._normalize_symbol(ticker)
        
        # 腾讯格式路由
        if self._is_us_stock(ticker):
            # 美股格式: usAAPL 或 usBRK.B
            # 腾讯对带点的代码支持很好
            tencent_symbol = f"us{symbol}"
        else:
            # A 股格式: sh600519 或 sz000001
            tencent_symbol = self._get_sina_symbol(symbol)
            
        url = f"http://qt.gtimg.cn/q={tencent_symbol}"
        
        loop = asyncio.get_event_loop()
        def fetch():
            _tls.bypass_proxy = True
            env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
            old_vals = {var: os.environ.get(var) for var in env_vars}
            for var in env_vars: os.environ.pop(var, None)
            
            try:
                resp = requests.get(url, timeout=2, proxies={'http': None, 'https': None})
                if resp.status_code == 200:
                    text = resp.text
                    # 格式: v_sz000001="51~平安银行~000001~10.90~10.87~..."
                    if '~' in text:
                        parts = text.split('~')
                        if len(parts) > 45:
                            # 提取基本面 (腾讯接口字段极其丰富)
                            additional = {}
                            if self._is_us_stock(ticker):
                                # 美股索引 (基于测试结果):
                                # 45: 总市值 (亿美元), 44: 市值 (可能是流通?), 47: 市盈率, 48: 52周最高, 49: 52周最低
                                # 注意: 腾讯返回的是亿美元
                                additional = {
                                    "market_cap": float(parts[45]) * 1e8 if parts[45] and parts[45] != '--' else None,
                                    "pe_ratio": float(parts[47]) if len(parts) > 47 and parts[47] and parts[47] != '--' else None,
                                    "fifty_two_week_high": float(parts[48]) if len(parts) > 48 and parts[48] and parts[48] != '--' else None,
                                    "fifty_two_week_low": float(parts[49]) if len(parts) > 49 and parts[49] and parts[49] != '--' else None,
                                }
                            else:
                                # A 股索引 (Tencent A-Share Specific):
                                # 39: 市净率 (PB), 44: 总市值 (亿), 45: 流通市值 (亿)
                                # 33: 52周最高, 34: 52周最低
                                additional = {
                                    "pb_ratio": float(parts[39]) if len(parts) > 39 and parts[39] and parts[39] != '--' else None,
                                    "market_cap": float(parts[44]) * 1e8 if len(parts) > 44 and parts[44] and parts[44] != '--' else None,
                                    "fifty_two_week_high": float(parts[33]) if len(parts) > 33 and parts[33] and parts[33] != '--' else None,
                                    "fifty_two_week_low": float(parts[34]) if len(parts) > 34 and parts[34] and parts[34] != '--' else None,
                                }
                                # A 股 PE 在腾讯接口中位置不固定，通常建议从 EM 补充，
                                # 如果非要从这里拿，parts[45] 往后可能有 PE 动态，但我们先保住市值。
                                additional["pe_ratio"] = float(parts[39]) if "pe" in str(parts[38]).lower() else None

                            return ProviderQuote(
                                ticker=ticker,
                                price=float(parts[3]),
                                change_percent=float(parts[32]),
                                name=parts[1],
                                last_updated=datetime.utcnow(),
                                additional_data=additional
                            )
                return None
            finally:
                for var, val in old_vals.items():
                    if val is not None: os.environ[var] = val
        
        return await loop.run_in_executor(None, fetch)

    async def _get_tencent_hist(self, ticker: str, num_days: int = 365) -> Optional[pd.DataFrame]:
        """从腾讯 K 线接口获取历史数据 (前复权)"""
        symbol = self._normalize_symbol(ticker)
        tencent_symbol = self._get_sina_symbol(symbol)
        # web.ifzq.gtimg.cn 接口支持前复权
        url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={tencent_symbol},day,,,{num_days},qfq"
        
        loop = asyncio.get_event_loop()
        def fetch():
            _tls.bypass_proxy = True
            try:
                # 环境强制禁用代理
                env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
                old_vals = {var: os.environ.get(var) for var in env_vars}
                for var in env_vars: os.environ.pop(var, None)
                
                try:
                    resp = requests.get(url, timeout=3, proxies={'http': None, 'https': None})
                    if resp.status_code == 200:
                        content = resp.text
                        if '=' in content:
                            json_str = content.split('=', 1)[1]
                            import json
                            data = json.loads(json_str)
                            stock_data = data.get("data", {}).get(tencent_symbol, {})
                            # 优先取前复权数据 qfqday
                            kline = stock_data.get("qfqday", stock_data.get("day", []))
                            if kline:
                                # 腾讯 K 线格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
                                df = pd.DataFrame(kline)
                                df = df.iloc[:, :6]
                                df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume']
                                df['Date'] = pd.to_datetime(df['Date'])
                                # 确保数值类型
                                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                # 调整列顺序以符合 indicator 计算习惯 (Date, Open, High, Low, Close, Volume)
                                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                                return df
                    return None
                finally:
                    for var, val in old_vals.items():
                        if val is not None: os.environ[var] = val
            except Exception as e:
                logger.error(f"Tencent hist fetch error for {ticker}: {e}")
                return None
        
        return await loop.run_in_executor(None, fetch)

    async def _get_sina_us_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """从新浪财经获取美股行情 (支持盘前/盘后感知 & 深度基本面提取)"""
        # 新浪美股代码映射
        sina_raw_ticker = self._map_us_sina_ticker(ticker)
        sina_ticker = f"gb_{sina_raw_ticker}"
        url = f"http://hq.sinajs.cn/list={sina_ticker}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn/"
        }

        loop = asyncio.get_event_loop()
        def fetch():
            _tls.bypass_proxy = True
            try:
                # 环境强制禁用代理
                env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
                old_vals = {var: os.environ.get(var) for var in env_vars}
                for var in env_vars: os.environ.pop(var, None)
                
                try:
                    resp = requests.get(url, headers=headers, timeout=3, proxies={'http': None, 'https': None})
                    if resp.status_code == 200:
                        content = resp.text
                        if '=' in content:
                            data_str = content.split('=', 1)[1].strip().strip(';').strip('"')
                            if not data_str: return None
                            data = data_str.split(',')
                            if len(data) < 30: return None
                            
                            # 新浪美股格式解析:
                            # 新浪美股格式解析:
                            # 0:名称, 1:现价, 2:涨跌额, 3:时间, 21:盘前盘后价, 24:盘前时间, 26:昨收
                            price = float(data[1])
                            name = data[0]
                            prev_close = float(data[26])
                            # 计算涨跌幅 (相比昨收)
                            change_percent = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                            
                            # 状态判定逻辑
                            status = MarketStatus.OPEN.value
                            pre_post_price = float(data[21]) if data[21] else 0.0
                            pre_post_time = data[24] # 例如 "Feb 27 09:06AM EST"
                            
                            if pre_post_price > 0 and pre_post_time:
                                if "AM" in pre_post_time:
                                    status = MarketStatus.PRE_MARKET.value
                                    price = pre_post_price
                                    change_percent = ((price - prev_close) / prev_close * 100) if prev_close > 0 else change_percent
                                elif "PM" in pre_post_time and "04:00PM" not in pre_post_time:
                                    status = MarketStatus.AFTER_HOURS.value
                                    price = pre_post_price
                                    change_percent = ((price - prev_close) / prev_close * 100) if prev_close > 0 else change_percent

                            return ProviderQuote(
                                ticker=ticker,
                                price=price,
                                change_percent=change_percent,
                                name=name,
                                last_updated=datetime.now(),
                                market_status=status,
                                # 扩展字段：临时存储解析出的基本面，以便 get_fundamental_data 复用
                                additional_data={
                                    "market_cap": float(data[12]) if len(data) > 12 and data[12] and data[12] != '--' else None,
                                    "pe_ratio": float(data[13]) if len(data) > 13 and data[13] and data[13] != '--' else None,
                                    "fifty_two_week_high": float(data[28]) if len(data) > 28 and data[28] and data[28] != '--' else None,
                                    "fifty_two_week_low": float(data[29]) if len(data) > 29 and data[29] and data[29] != '--' else None,
                                    "eps": float(data[17]) if len(data) > 17 and data[17] and data[17] != '--' else None,
                                }
                            )
                    return None
                finally:
                    for var, val in old_vals.items():
                        if val is not None: os.environ[var] = val
            except Exception as e:
                logger.error(f"Sina US fetch error for {ticker}: {e}")
                return None
        
        return await loop.run_in_executor(None, fetch)

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """获取行情，智能路由 A 股或美股"""
        # 第一优先级：Tencent 实时行情 (直连性最好，支持美股基本面，极速响应)
        try:
            tencent_quote = await self._get_tencent_quote(ticker)
            if tencent_quote:
                return tencent_quote
        except Exception as e:
            logger.warning(f"Tencent quote fetch failed for {ticker}: {e}")

        if self._is_us_stock(ticker):
            # 美股回退：新浪财经 (国内直连)
            quote = await self._get_sina_us_quote(ticker)
            if quote: return quote
            return None
            
        symbol = self._normalize_symbol(ticker)
        
        # 1. 第一优先级：Tencent 实时行情 (目前连通性最好，极速响应)
        try:
            tencent_quote = await self._get_tencent_quote(ticker)
            if tencent_quote:
                return tencent_quote
        except Exception as e:
            logger.warning(f"Tencent quote fetch failed for {ticker}: {e}")

        try:
            # 2. 第二优先级：从全量实时缓存获取
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

            # 3. 兜底路径 A：Sina 实时行情
            try:
                sina_symbol = self._get_sina_symbol(symbol)
                sina_df = await self._run_sync(ak.stock_zh_a_spot, symbol=sina_symbol)
                if sina_df is not None and not sina_df.empty:
                    target = sina_df.iloc[0]
                    return ProviderQuote(
                        ticker=ticker,
                        price=float(target.get('now', 0)),
                        change_percent=0.0,
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
            high, low = None, None
            
            # --- 优先级 1: 腾讯行情源 (包含 PE, 市值, 52周高低) ---
            # 腾讯接口在服务器直连环境下极其稳定
            try:
                t_quote = await self._get_tencent_quote(ticker)
                if t_quote and t_quote.additional_data:
                    ad = t_quote.additional_data
                    name = t_quote.name
                    pe = ad.get("pe_ratio")
                    mc = ad.get("market_cap")
                    high = ad.get("fifty_two_week_high")
                    low = ad.get("fifty_two_week_low")
                    if pe and pe > 0:
                        eps = t_quote.price / pe
            except Exception as te:
                logger.warning(f"Tencent fundamental fetch failed for {ticker}: {te}")

            # --- 优先级 2: 东方财富个股信息 (补充行业/板块) ---
            # 包裹 try-except 以应对连接中断
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    sector = data.get('行业')
                    if not mc: mc = float(data.get('总市值', 0))
                    if not name: name = data.get('股票简称')
            except Exception as e:
                logger.warning(f"EM individual info failed for {ticker} (likely connection reset): {e}")

            return ProviderFundamental(
                name=name, 
                sector=sector, 
                industry=sector, 
                market_cap=mc, 
                pe_ratio=pe, 
                eps=eps,
                fifty_two_week_high=high,
                fifty_two_week_low=low
            )
        except Exception as e:
            logger.error(f"AkShare get_fundamental_data error for {ticker}: {e}")
            return None

    async def _get_us_fundamental(self, ticker: str) -> Optional[ProviderFundamental]:
        """美股基础面增强 (国内直连版)"""
        try:
            # 1. 第一优先级：从腾讯行情中提取 (数据最新，且支持 BRK.B 等点号代码)
            quote = await self._get_tencent_quote(ticker)
            if quote and hasattr(quote, 'additional_data') and quote.additional_data:
                ad = quote.additional_data
                if ad.get("market_cap"): # 确保有核心数据
                    return ProviderFundamental(
                        name=quote.name,
                        market_cap=ad.get("market_cap"),
                        pe_ratio=ad.get("pe_ratio"),
                        eps=ad.get("eps"),
                        fifty_two_week_high=ad.get("fifty_two_week_high"),
                        fifty_two_week_low=ad.get("fifty_two_week_low")
                    )

            # 2. 第二优先级：新浪财经 (HQ 包含基本面)
            quote = await self._get_sina_us_quote(ticker)
            if quote and hasattr(quote, 'additional_data') and quote.additional_data:
                ad = quote.additional_data
                if ad.get("market_cap"):
                    return ProviderFundamental(
                        name=quote.name,
                        market_cap=ad.get("market_cap"),
                        pe_ratio=ad.get("pe_ratio"),
                        eps=ad.get("eps"),
                        fifty_two_week_high=ad.get("fifty_two_week_high"),
                        fifty_two_week_low=ad.get("fifty_two_week_low")
                    )
            
            # 2. 兜底：从东财缓存拿
            name, pe, mc = ticker, None, None
            high, low, eps = None, None, None
            if AkShareProvider._cached_us_spot_df is not None:
                # 兼容性匹配 (东方财富美股代码可能带后缀)
                df = AkShareProvider._cached_us_spot_df
                row = df[df['代码'].str.contains(ticker, na=False)]
                if not row.empty:
                    target = row.iloc[0]
                    name = str(target.get('名称', ticker))
                    pe = float(target.get('市盈率', 0))
                    mc = float(target.get('总市值', 0))
                    high = float(target.get('最高', 0))
                    low = float(target.get('最低', 0))
                    # 估算 EPS
                    price = float(target.get('最新价', 0))
                    if pe and pe > 0: eps = price / pe
                    
            return ProviderFundamental(
                name=name, 
                market_cap=mc, 
                pe_ratio=pe, 
                eps=eps,
                fifty_two_week_high=high,
                fifty_two_week_low=low
            )
        except Exception as e:
            logger.error(f"AkShare _get_us_fundamental error: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Dict[str, Any]]:
        # 严格过滤测试标的，避免请求外部接口
        if ticker.upper().startswith("TEST_"):
            logger.info(f"Skipping historical data fetch for test ticker: {ticker}")
            return None
            
        try:
            if self._is_us_stock(ticker):
                df = await self._run_sync(ak.stock_us_daily, symbol=ticker)
                if df is not None and not df.empty:
                    df = df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
            else:
                # A 股改用腾讯源，绕开被封锁的东财/AkShare 原生接口
                df = await self._get_tencent_hist(ticker, num_days=250)
                if df is not None and not df.empty:
                    df.set_index('Date', inplace=True)
                else:
                    # 备选：原有的 AkShare 方式
                    symbol = self._normalize_symbol(ticker)
                    df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
                    if df is not None and not df.empty:
                        # 严格检查列是否存在，防止重命名报错
                        if '日期' in df.columns:
                            df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})
                            df['Date'] = pd.to_datetime(df['Date'])
                            df.set_index('Date', inplace=True)
                        else:
                            return None
            
            # 最终检查 DataFrame 是否有效且包含足够数据点
            if df is None or df.empty or len(df) < 2: 
                return None
                
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
                # A 股改用腾讯源
                df = await self._get_tencent_hist(ticker, num_days=500)
                if df is None or df.empty:
                    # 备选
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
