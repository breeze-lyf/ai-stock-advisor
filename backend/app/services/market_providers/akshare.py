import time
import functools
import random
import akshare as ak
import pandas as pd
import logging
import asyncio
import os
import requests
import json
import subprocess
import urllib3
from io import StringIO
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from app.utils.time import utc_now_naive

def retry_on_network_error(max_retries=3, initial_delay=1):
    """
    针对网络波动的重试装饰器。
    支持处理 RemoteDisconnected, ConnectionResetError, ProxyError 等。

    优化后的策略：
    - 固定延迟退避（非指数），避免请求堆积
    - 添加随机抖动，防止同步触发
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            delay = initial_delay
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException,
                        urllib3.exceptions.HTTPError,
                        ConnectionError,
                        TimeoutError) as e:
                    last_err = e
                    if i < max_retries:
                        # 固定延迟 + 抖动，避免指数退避导致请求堆积
                        sleep_time = delay + random.uniform(0.5, 1.5)
                        logger.warning(f"Network error in {func.__name__}, retrying ({i+1}/{max_retries}) in {sleep_time:.2f}s: {e}")
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise last_err
            return None
        return wrapper
    return decorator

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
from app.core.config import settings

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
    _cached_hk_spot_df = None
    _last_hk_spot_update = 0
    _cached_fund_df = None
    _last_fund_update = 0
    
    _async_lock = None
    _CACHE_TTL = 300  # 缓存有效期 5 分钟（降低更新频率）

    @classmethod
    def _get_semaphore(cls):
        if cls._async_lock is None:
            # 优化：允许 3 个并发，平衡反爬和性能
            # 原逻辑：Semaphore(1) 强制串行，导致请求堆积触发反爬
            cls._async_lock = asyncio.Semaphore(3)
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
                    for var in env_vars:
                        os.environ.pop(var, None)
                    
                    try:
                        with requests.Session() as s:
                            s.trust_env = False
                            # 核心修复：硬编码直连环境，消除本地 Clash 等代理干扰
                            s.proxies = {'http': None, 'https': None}
                            
                            @retry_on_network_error(max_retries=2)
                            def _inner_fetch():
                                return ak.stock_zh_a_spot_em()
                            return _inner_fetch()
                    finally:
                        _tls.bypass_proxy = False
                        for var, val in old_vals.items():
                            if val is not None:
                                os.environ[var] = val

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
        在线程池中运行同步函数。
        默认强制直连（历史行为），可通过 AKSHARE_BYPASS_PROXY=false 允许走系统代理。
        """
        def run_isolated():
            bypass_proxy = getattr(settings, "AKSHARE_BYPASS_PROXY", True)
            if bypass_proxy:
                _tls.bypass_proxy = True
                env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'NO_PROXY']
                old_vals = {var: os.environ.get(var) for var in env_vars}
                for var in env_vars:
                    os.environ.pop(var, None)
            else:
                _tls.bypass_proxy = False
                old_vals = {}

            try:
                with requests.Session() as s:
                    # bypass=true 时禁用系统代理；否则允许读取环境代理
                    s.trust_env = not bypass_proxy
                    if bypass_proxy:
                        # 核心修复点：强制解除本地代理对同步任务的干扰
                        s.proxies = {'http': None, 'https': None}

                    if func == requests.get:
                        return s.get(*args, **kwargs)
                    if func == requests.post:
                        return s.post(*args, **kwargs)
                    return func(*args, **kwargs)
            finally:
                _tls.bypass_proxy = False
                for var, val in old_vals.items():
                    if val is not None:
                        os.environ[var] = val

        loop = asyncio.get_event_loop()
        async with self._get_semaphore():
            return await loop.run_in_executor(None, run_isolated)

    async def _run_sync_force_proxy(self, func, *args, **kwargs):
        """
        在线程池中运行同步函数，并强制启用代理（忽略 NO_PROXY）。
        场景：美股历史接口在部分网络环境下仅可通过代理访问。
        """
        def run_with_forced_proxy():
            _tls.bypass_proxy = False
            old_env = {}
            proxy = (getattr(settings, "HTTPS_PROXY", None) or getattr(settings, "HTTP_PROXY", None) or "").strip()
            if proxy:
                for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"]:
                    old_env[key] = os.environ.get(key)
                os.environ["HTTP_PROXY"] = proxy
                os.environ["HTTPS_PROXY"] = proxy
                os.environ["http_proxy"] = proxy
                os.environ["https_proxy"] = proxy
                # 强制走代理，避免 eastmoney 被 NO_PROXY 误绕过
                os.environ.pop("NO_PROXY", None)
                os.environ.pop("no_proxy", None)

            try:
                with requests.Session() as s:
                    s.trust_env = True
                    if func == requests.get:
                        return s.get(*args, **kwargs)
                    if func == requests.post:
                        return s.post(*args, **kwargs)
                    return func(*args, **kwargs)
            finally:
                _tls.bypass_proxy = False
                if proxy:
                    for key, val in old_env.items():
                        if val is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = val

        loop = asyncio.get_event_loop()
        async with self._get_semaphore():
            return await loop.run_in_executor(None, run_with_forced_proxy)

    @classmethod
    async def _update_hk_spot_cache(cls):
        async with cls._get_semaphore():
            now = time.time()
            if cls._cached_hk_spot_df is not None and (now - cls._last_hk_spot_update) < cls._CACHE_TTL:
                return

            try:
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, ak.stock_hk_spot_em)
                if df is not None and not df.empty:
                    cls._cached_hk_spot_df = df
                    cls._last_hk_spot_update = now
            except Exception as e:
                logger.error(f"Failed to update AkShare HK spot cache: {e}")

    @classmethod
    async def _update_fund_cache(cls):
        async with cls._get_semaphore():
            now = time.time()
            if cls._cached_fund_df is not None and (now - cls._last_fund_update) < cls._CACHE_TTL:
                return

            try:
                loop = asyncio.get_event_loop()

                def fetch():
                    frames = []
                    for func in (ak.fund_etf_spot_em, ak.fund_name_em):
                        try:
                            df = func()
                            if df is not None and not df.empty:
                                frames.append(df)
                        except Exception:
                            continue
                    if not frames:
                        return None
                    return pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()

                df = await loop.run_in_executor(None, fetch)
                if df is not None and not df.empty:
                    cls._cached_fund_df = df
                    cls._last_fund_update = now
            except Exception as e:
                logger.error(f"Failed to update AkShare fund cache: {e}")

    @staticmethod
    def _extract_search_results(
        df: Optional[pd.DataFrame],
        query: str,
        *,
        code_columns: list[str],
        name_columns: list[str],
        suffix: str = "",
        limit: int = 10,
    ) -> list[dict[str, str]]:
        if df is None or df.empty:
            return []

        query_lower = query.strip().lower()
        if not query_lower:
            return []

        code_col = next((col for col in code_columns if col in df.columns), None)
        name_col = next((col for col in name_columns if col in df.columns), None)
        if not code_col or not name_col:
            return []

        work_df = df[[code_col, name_col]].copy()
        work_df[code_col] = work_df[code_col].astype(str).str.strip()
        work_df[name_col] = work_df[name_col].astype(str).str.strip()
        mask = (
            work_df[code_col].str.lower().str.contains(query_lower, na=False)
            | work_df[name_col].str.lower().str.contains(query_lower, na=False)
        )
        matched = work_df[mask].drop_duplicates(subset=[code_col]).head(limit)

        results: list[dict[str, str]] = []
        for _, row in matched.iterrows():
            ticker = str(row[code_col]).strip().upper()
            name = str(row[name_col]).strip() or ticker
            if suffix and not ticker.endswith(suffix):
                ticker = f"{ticker}{suffix}"
            results.append({"ticker": ticker, "name": name})
        return results

    async def search_instruments(self, query: str, limit: int = 20) -> list[dict[str, str]]:
        """
        搜索 A 股/港股/美股/基金工具

        Args:
            query: 搜索关键词（股票代码、名称拼音等）
            limit: 最大返回结果数量（默认 20）

        Returns:
            搜索结果列表，每个结果包含 ticker 和 name 字段
        """
        await self._update_spot_cache()
        await self._update_hk_spot_cache()
        await self._update_fund_cache()

        results: list[dict[str, str]] = []
        seen: set[str] = set()

        datasets = [
            (
                AkShareProvider._cached_spot_df,
                {"code_columns": ["代码"], "name_columns": ["名称"], "suffix": ""},
            ),
            (
                AkShareProvider._cached_hk_spot_df,
                {"code_columns": ["代码"], "name_columns": ["名称"], "suffix": ".HK"},
            ),
            (
                AkShareProvider._cached_fund_df,
                {
                    "code_columns": ["代码", "基金代码"],
                    "name_columns": ["名称", "基金简称", "基金名称"],
                    "suffix": "",
                },
            ),
            (
                AkShareProvider._cached_us_spot_df,
                {"code_columns": ["代码"], "name_columns": ["名称"], "suffix": ""},
            ),
        ]

        if AkShareProvider._cached_us_spot_df is None:
            try:
                now = time.time()
                async with self._get_semaphore():
                    # 优先尝试直连获取东财美股
                    us_df = await self._run_sync(ak.stock_us_spot_em)
                    if us_df is not None and not us_df.empty:
                        AkShareProvider._cached_us_spot_df = us_df
                        AkShareProvider._last_us_spot_update = now
                
                # 更新对应数据集索引
                datasets[-1] = (
                    AkShareProvider._cached_us_spot_df,
                    {"code_columns": ["代码"], "name_columns": ["名称"], "suffix": ""},
                )
            except Exception as e:
                logger.warning(f"AkShare US search cache update failed, attempting Tencent Fallback for {query}: {e}")
                # 核心修复点：针对单个 Query 的 Tencent 行情 Fallback 逻辑
                if not any(item["ticker"] == query.upper() for item in results):
                    try:
                        quote = await self._get_tencent_quote(query)
                        if quote:
                            results.append({"ticker": quote.ticker, "name": quote.name or quote.ticker})
                            seen.add(quote.ticker.upper())
                    except Exception as te:
                        logger.error(f"Tencent search fallback failed for {query}: {te}")

        for df, options in datasets:
            matches = self._extract_search_results(df, query, limit=limit, **options)
            for item in matches:
                if item["ticker"] in seen:
                    continue
                seen.add(item["ticker"])
                results.append(item)
                if len(results) >= limit:
                    return results

        return results

    def _normalize_symbol(self, ticker: str) -> str:
        """
        代码归一化: 002050.SZ -> 002050
        注意: 对于美股 (如 BRK.B)，我们要保留点号，因为腾讯接口支持带点的原貌。
        对于指数 (^GSPC)，我们要将其映射为腾讯支持的格式 (.INX)。
        """
        if not ticker: return ticker
        
        # 处理美股指数映射
        if ticker.startswith('^'):
            index_map = {
                "^GSPC": ".INX",
                "^IXIC": ".IXIC",
                "^DJI": ".DJI",
            }
            return index_map.get(ticker.upper(), ticker.upper())

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

    @retry_on_network_error(max_retries=1)
    async def _get_us_hist_em_df(self, ticker: str, num_days: int = 250, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        使用东方财富美股历史接口获取 K 线，避免 stock_us_daily 对 py_mini_racer 的依赖。
        说明：
        - secid 前缀常见为 105/106/107（NASDAQ/NYSE/AMEX）
        - 逐个尝试直到拿到非空数据
        """
        symbol = ticker.upper().strip()
        secid_candidates = [
            f"105.{symbol}",
            f"106.{symbol}",
            f"107.{symbol}",
        ]

        last_error: Optional[Exception] = None
        for secid in secid_candidates:
            try:
                # 尝试 1: 直接获取 (东财)
                df = await self._run_sync(
                    ak.stock_us_hist,
                    symbol=secid,
                    period="daily",
                    start_date="19700101",
                    end_date=end_date.replace("-", "") if end_date else "20500101",
                    adjust="qfq",
                )
                
                # 尝试 2: 强制代理获取 (东财)
                if df is None or df.empty:
                    try:
                        df = await self._run_sync_force_proxy(
                            ak.stock_us_hist,
                            symbol=secid,
                            period="daily",
                            start_date="19700101",
                            end_date=end_date.replace("-", "") if end_date else "20500101",
                            adjust="qfq",
                        )
                    except Exception as proxy_e:
                        last_error = proxy_e
                        logger.warning(f"EM hist (force proxy) failed for {ticker} with secid: {secid}: {proxy_e}")

                if df is None or df.empty:
                    continue

                # 东方财富映射
                rename_map = {
                    "日期": "Date",
                    "开盘": "Open",
                    "最高": "High",
                    "最低": "Low",
                    "收盘": "Close",
                    "成交量": "Volume",
                }
                if "日期" in df.columns:
                    df = df.rename(columns=rename_map)
                    keep_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
                    df = df[[c for c in keep_cols if c in df.columns]].copy()
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    return df.dropna(subset=["Date"]).tail(num_days)
            except Exception as e:
                last_error = e
                # 候选测试期间降低日志级别
                logger.debug(f"EM hist attempt for {ticker} with secid {secid} failed: {e}")
                continue

    async def _get_us_hist_em_direct(self, ticker: str, num_days: int = 250, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """直接请求东方财富 API 获取 K 线 (支持美股/A股)，绕过 AkShare 封装以提高连通性"""
        symbol = ticker.upper().strip()
        last_error = None
        
        # 识别候选 secid: 
        # 105: NASDAQ, 106: NYSE, 107: AMEX
        # 0: 深交所, 1: 上交所
        if self._is_us_stock(ticker):
             secid_candidates = [f"105.{symbol}", f"106.{symbol}", f"107.{symbol}"]
             # 尝试从缓存获取确切的 secid
             if AkShareProvider._cached_us_spot_df is not None:
                 df_spot = AkShareProvider._cached_us_spot_df
                 row = df_spot[df_spot['代码'].str.contains(symbol, na=False)]
                 if not row.empty:
                     exact_secid = str(row.iloc[0]['代码'])
                     if '.' in exact_secid:
                         secid_candidates = [exact_secid] + [c for c in secid_candidates if c != exact_secid]
        else:
             numeric_symbol = "".join(filter(str.isdigit, symbol))
             if symbol.endswith(".SH") or numeric_symbol.startswith("6"):
                 secid_candidates = [f"1.{numeric_symbol}"]
             else:
                 secid_candidates = [f"0.{numeric_symbol}"]

        loop = asyncio.get_event_loop()
        
        for secid in secid_candidates:
            try:
                # 字段说明: f51:日期, f52:开盘, f53:收盘, f54:最高, f55:最低, f56:成交量
                # klt=101:日线, fqt=1:前复权
                end_str = end_date.replace("-", "") if end_date else "20500101"
                url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end={end_str}&lmt={num_days}"
                
                def fetch_em():
                    _tls.bypass_proxy = True
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://quote.eastmoney.com/",
                        "Connection": "close"
                    }
                    # 环境级禁用代理
                    old_proxies = {var: os.environ.get(var) for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']}
                    for var in old_proxies:
                        if var in os.environ: del os.environ[var]
                    try:
                        resp = requests.get(url, headers=headers, timeout=5, proxies={'http': None, 'https': None})
                        if resp.status_code == 200:
                            return resp.json()
                        return None
                    finally:
                        for var, val in old_proxies.items():
                            if val: os.environ[var] = val

                res_json = await loop.run_in_executor(None, fetch_em)
                if not res_json or not res_json.get("data") or not res_json["data"].get("klines"):
                    continue
                
                klines = res_json["data"]["klines"]
                rows = [k.split(',') for k in klines]
                df = pd.DataFrame(rows, columns=['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'CHG', 'CHG_PCT', 'TURNOVER', 'AMT', 'AMPLITUDE'])
                
                # 类型转换
                df['Date'] = pd.to_datetime(df['Date'])
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                if df is not None and not df.empty:
                    logger.info(f"✅ [AkShareProvider] Direct EM fetch success for {secid}, len={len(df)}")
                    return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            except Exception as e:
                last_error = e
                # 候选试错阶段，对连接性错误已降级，非核心错误日志
                if "RemoteDisconnected" in str(e) or "Connection aborted" in str(e):
                    logger.debug(f"Direct EM hist attempt failed for {secid}: {e}")
                else:
                    logger.warning(f"Direct EM hist attempt failed for {secid}: {e}")
                continue

        # 尝试 3: 优先尝试腾讯源 (由于其高频连通性更好)
        try:
            logger.info(f"🔍 [AkShareProvider] EM failed, trying Tencent backup for {ticker}")
            df = await self._get_tencent_hist(ticker, num_days=num_days, end_date=end_date)
            # 校验数据量，防止腾讯源只返回 2 条极简数据 (起止点)
            if df is not None and len(df) > 10:
                logger.info(f"✅ [AkShareProvider] Tencent backup fetch success for {ticker}, len={len(df)}")
                return df
            elif df is not None:
                logger.warning(f"⚠️ [AkShareProvider] Tencent backup for {ticker} returned only {len(df)} rows (incomplete), skipping...")
        except Exception as te:
            logger.warning(f"⚠️ [AkShareProvider] Tencent backup failed for {ticker}: {te}")

        # 尝试 4: 新浪 Subprocess Fallback (仅作为最后的稳健手段)
        try:
            logger.info(f"🔍 [AkShareProvider] Tencent failed, trying Sina subprocess for {ticker}")
            
            # 使用相对路径寻找脚本
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "utils", "fetch_us_stock.py")
            if os.path.exists(script_path):
                args = ["python3", script_path, ticker]
                if end_date: args.append(end_date)
                
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and stdout:
                    raw_data = stdout.decode().strip()
                    if raw_data.startswith("["):
                        from io import StringIO
                        df_sina = pd.read_json(StringIO(raw_data))
                        if df_sina is not None and not df_sina.empty:
                            logger.info(f"✅ [AkShareProvider] Sina subprocess success for {ticker}, len={len(df_sina)}")
                            rename_sina = {
                                "date": "Date",
                                "open": "Open",
                                "high": "High",
                                "low": "Low",
                                "close": "Close",
                                "volume": "Volume"
                            }
                            df_sina = df_sina.rename(columns=rename_sina)
                            df_sina["Date"] = pd.to_datetime(df_sina["Date"], errors="coerce").dt.date
                            for col in ["Open", "High", "Low", "Close", "Volume"]:
                                if col in df_sina.columns:
                                    df_sina[col] = pd.to_numeric(df_sina[col], errors="coerce")
                            return df_sina.dropna(subset=["Date", "Close"]).tail(num_days)
            else:
                logger.warning(f"⚠️ [AkShareProvider] Sina script not found at {script_path}")
        except Exception as se:
            logger.warning(f"⚠️ [AkShareProvider] Sina subprocess failed for {ticker}: {se}")

        if last_error:
            logger.warning(
                f"⚠️ [AkShareProvider] All domestic sources failed for {ticker}, error: {last_error}. "
                "AKSHARE mode will not fall back to Yahoo."
            )
        return None

    async def _get_yahoo_hist(self, ticker: str, num_days: int = 250) -> Optional[pd.DataFrame]:
        """Yahoo Finance Chart API 兜底 (针对某些标的在国内源数据残缺的情况)"""
        symbol = ticker.upper().strip()
        # 转换一些特殊代码 (指数)
        if symbol == ".INX": symbol = "^GSPC"
        elif symbol == ".IXIC": symbol = "^IXIC"
        elif symbol == ".DJI": symbol = "^DJI"
        
        # 映射合理的时间跨度
        if num_days <= 30: r = "1mo"
        elif num_days <= 95: r = "3mo"
        elif num_days <= 190: r = "6mo"
        elif num_days <= 380: r = "1y"
        else: r = "max"
        
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={r}"
        
        try:
            import httpx
            # 注意: 这里保持默认代理环境，因为用户环境中的雅虎连通性经测试(test_yahoo_nvda.py)是良好的
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    result = data.get("chart", {}).get("result", [{}])[0]
                    timestamps = result.get("timestamp", [])
                    indicators = result.get("indicators", {}).get("quote", [{}])[0]
                    adj_close = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
                    
                    if not timestamps: return None
                    
                    # 优先取复权收盘价 adj_close
                    close_prices = adj_close if adj_close else indicators.get("close")
                    
                    df = pd.DataFrame({
                        "Date": pd.to_datetime(timestamps, unit='s'),
                        "Open": indicators.get("open"),
                        "High": indicators.get("high"),
                        "Low": indicators.get("low"),
                        "Close": close_prices,
                        "Volume": indicators.get("volume")
                    })
                    return df.dropna(subset=["Date", "Close"]).tail(num_days)
        except Exception as e:
            logger.debug(f"Yahoo hist fetch failed for {ticker}: {e}")
        return None

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
            # 美股格式: usAAPL 或 usBRK.B 或 us.INX
            # 腾讯支持 us.INX 这种带点的指数代码
            if symbol.startswith('.'):
                tencent_symbol = f"us{symbol}"
            else:
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
                                last_updated=utc_now_naive(),
                                additional_data=additional
                            )
                return None
            finally:
                for var, val in old_vals.items():
                    if val is not None: os.environ[var] = val
        
        return await loop.run_in_executor(None, fetch)

    async def _get_tencent_hist(self, ticker: str, num_days: int = 365, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """从腾讯 K 线接口获取历史数据 (前复权)"""
        symbol = self._normalize_symbol(ticker)
        if self._is_us_stock(ticker):
            tencent_symbol = f"us{symbol}"
        else:
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
                            data_root = data.get("data", {})
                            if isinstance(data_root, list):
                                # If data_root is a list, it means Tencent returned empty or failed data in an unexpected format.
                                logger.info(f"Tencent returned 'data' as a list for {ticker}, expected a dict (no data).")
                                return None
                                
                            stock_data = data_root.get(tencent_symbol, {})
                            if not isinstance(stock_data, dict):
                                # Ensure stock_data is a dict before calling .get()
                                stock_data = {}
                                
                            if not stock_data:
                                # 容错：部分标的返回 key 可能是无前缀代码
                                stock_data = data_root.get(symbol, {})
                                if not isinstance(stock_data, dict):
                                    stock_data = {}
                            
                            if not stock_data and data_root:
                                # Final attempt to find any dictionary among values
                                for val in data_root.values():
                                    if isinstance(val, dict):
                                        stock_data = val
                                        break
                            # 优先取前复权数据 qfqday
                            kline = stock_data.get("qfqday", stock_data.get("day", []))
                            if kline:
                                # 数据格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
                                # 取最后 num_days 条以确保获取最新数据
                                kline_sliced = kline[-num_days:]
                                df = pd.DataFrame(kline_sliced)
                                df = df.iloc[:, :6]
                                df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume']
                                df['Date'] = pd.to_datetime(df['Date'])
                                # 确保数值类型
                                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                                # 调整列顺序以符合 indicator 计算习惯 (Date, Open, High, Low, Close, Volume)
                                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                                if end_date:
                                    # 过滤在该日期之前的数据
                                    target_dt = pd.to_datetime(end_date)
                                    df = df[df['Date'] < target_dt]
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
            # 1. 优先使用腾讯源 (腾讯源支持美股指数 .INX 等)
            try:
                quote = await self._get_tencent_quote(ticker)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(f"Tencent US quote fetch failed for {ticker}: {e}")
            
            # 2. 备选方案：新浪或东财
            try:
                quote = await self._get_us_quote(ticker)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(f"AkShare US quote fallback failed for {ticker}: {e}")
            
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
                        last_updated=utc_now_naive()
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
                        last_updated=utc_now_naive()
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
                        last_updated=utc_now_naive()
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
                return ProviderQuote(ticker=ticker, price=price, change_percent=change_percent, name=name or ticker, last_updated=utc_now_naive())

            return None
        except Exception as e:
            logger.error(f"AkShare get_quote error for {ticker}: {e}")
            return None

    async def _get_us_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """专用于获取美股行情的内部方法，包含国内直连回退机制"""
        try:
            # 兼容性逻辑：判断是否为指数 (Index)
            is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI", "^GSPC", "^IXIC", "^DJI"]
            
            # 归一化指数代码
            search_ticker = ticker.upper()
            if search_ticker == "^GSPC": search_ticker = ".INX"
            elif search_ticker == "^IXIC": search_ticker = ".IXIC"
            elif search_ticker == "^DJI": search_ticker = ".DJI"
            else: search_ticker = ticker
            
            # --- 极速路径 1：直接从 Yahoo 底层 API 获取 (通常需要代理) ---
            live_price = None
            try:
                import httpx
                # 只有在可能访问雅虎时才使用 3s 短超时
                async with httpx.AsyncClient(timeout=3.0) as client:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    # Yahoo 使用原始 ticker，注意：这会读取系统 HTTP_PROXY
                    res = await client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{search_ticker}?interval=1m&range=1d", headers=headers)
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
                    last_updated=utc_now_naive()
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
                            last_updated=utc_now_naive()
                        )
            except Exception as e:
                logger.error(f"AkShare US spot fallback failed for {ticker}: {e}")

            # --- 最终兜底：拉取历史数据取最后一条 ---
            hist_df = None
            if is_index:
                try:
                    hist_df = await self._get_tencent_hist(ticker, num_days=180)
                except:
                    pass
            
            if hist_df is None or hist_df.empty:
                try:
                    hist_df = await self._get_us_hist_em_df(ticker)
                except:
                    pass
                
            if hist_df is not None and not hist_df.empty:
                latest = hist_df.iloc[-1]
                close_key = 'Close' if 'Close' in latest else 'close'
                return ProviderQuote(
                    ticker=ticker,
                    price=float(latest.get(close_key, 0)),
                    change_percent=0.0,
                    name=ticker, 
                    last_updated=utc_now_naive()
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
            # 包裹 try-except 并增加重试
            try:
                @retry_on_network_error(max_retries=1)
                def fetch_em_info():
                    return ak.stock_individual_info_em(symbol=symbol)

                info_df = await self._run_sync(fetch_em_info)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    sector = data.get('行业')
                    if not mc: 
                        mc_val = data.get('总市值', 0)
                        if mc_val and mc_val != '-': mc = float(mc_val)
                    if not name: name = data.get('股票简称')
            except Exception as e:
                if "all scalar values" in str(e):
                    logger.info(f"EM individual info for {ticker} unavailable (no data found).")
                elif "RemoteDisconnected" in str(e):
                    # 东财服务器主动断开，可能是 IP 被限流，降级为 INFO 避免日志噪声
                    logger.info(f"EM individual info for {ticker} unavailable (server rate limit).")
                else:
                    logger.warning(f"EM individual info failed for {ticker} (likely connection reset): {e}")

            # --- 优先级 3: 直接请求 East Money API (如果 AkShare 失败) ---
            if not mc or not sector:
                try:
                    loop = asyncio.get_event_loop()
                    mkt = 1 if symbol.startswith(('60', '68')) else 0
                    # f58: 名称, f127: 行业, f116: 总市值, f43: 最新价, f170: 涨跌幅
                    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={mkt}.{symbol}&fields=f58,f127,f116,f43,f170"
                    
                    @retry_on_network_error(max_retries=1)
                    def direct_fundamental():
                        _tls.bypass_proxy = True
                        try:
                            resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"}, proxies={'http': None, 'https': None})
                            return resp.json() if resp.status_code == 200 else None
                        finally:
                            _tls.bypass_proxy = False
                    
                    res_json = await loop.run_in_executor(None, direct_fundamental)
                    if res_json and "data" in res_json and res_json["data"]:
                        d = res_json["data"]
                        if not name: name = d.get('f58')
                        if not sector: sector = d.get('f127')
                        if not mc: mc = float(d.get('f116', 0))
                except Exception as direct_e:
                    if "RemoteDisconnected" in str(direct_e):
                        # 东财 API 被限流，降级为 INFO
                        logger.info(f"Direct EM fundamental unavailable for {ticker} (server rate limit).")
                    else:
                        logger.warning(f"Direct EM fundamental fallback failed for {ticker}: {direct_e}")

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

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo", end_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # 严格过滤测试标的，避免请求外部接口
        if ticker.upper().startswith("TEST_"):
            logger.info(f"Skipping historical data fetch for test ticker: {ticker}")
            return None
            
        try:
            if self._is_us_stock(ticker):
                # 美股指数和个股抓取策略区分
                is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI", "^GSPC", "^IXIC", "^DJI"]
                df = None
                
                if is_index:
                    # 指数优先走腾讯 K 线
                    logger.info(f"DEBUG: Attempting Tencent hist for US index {ticker}")
                    df = await self._get_tencent_hist(ticker, num_days=1000, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: Tencent hist for US index {ticker} success, len={len(df)}")
                    else:
                        logger.info(f"DEBUG: Tencent hist for US index {ticker} failed.")

                if df is None or df.empty:
                    # 尝试 1: 直接 EM API (加 50 天做指标预热)
                    days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 250, "5y": 1250}
                    req_days = days_map.get(period, 250)
                    logger.info(f"DEBUG: Attempting Direct EM API for {ticker}, end_date={end_date}, days={req_days+50}")
                    df = await self._get_us_hist_em_direct(ticker, num_days=req_days + 50, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: Direct EM API for {ticker} success, len={len(df)}")
                    else:
                        logger.info(f"DEBUG: Direct EM API for {ticker} failed.")
                
                if df is None or df.empty:
                    # 尝试 2: 腾讯源 (US 股票备选)
                    logger.info(f"DEBUG: Attempting Tencent hist for {ticker}")
                    df = await self._get_tencent_hist(ticker, num_days=req_days + 50, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: Tencent hist for {ticker} success, len={len(df)}")
                    else:
                        logger.info(f"DEBUG: Tencent hist for {ticker} failed.")

                if df is None or df.empty:
                    # 尝试 3: 原有的 AkShare EM (最后兜底)
                    logger.info(f"DEBUG: Attempting AkShare EM hist for {ticker}")
                    df = await self._get_us_hist_em_df(ticker, num_days=req_days + 50, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: AkShare EM hist for {ticker} success, len={len(df)}")
                    else:
                        logger.info(f"DEBUG: AkShare EM hist for {ticker} failed.")

                if df is not None and not df.empty:
                    df = df.sort_values("Date")
                    df.set_index('Date', inplace=True)
            else:
                # A 股：优先使用 AkShare 原生接口（最快，约 0.2 秒），失败后再 fallback 到其他源
                days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 250, "5y": 1250}
                req_days = days_map.get(period, 250)

                df = None
                symbol = self._normalize_symbol(ticker)

                # 路径 1: AkShare 原生接口 (最快，直连东方财富)
                @retry_on_network_error(max_retries=2)
                def _fetch_hist():
                    return ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                df = await self._run_sync(_fetch_hist)
                if df is not None and not df.empty:
                    logger.info(f"DEBUG: AkShare native hist for A-share {ticker} success, len={len(df)}")
                    if '日期' in df.columns:
                        df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})
                        df['Date'] = pd.to_datetime(df['Date'])
                        df.set_index('Date', inplace=True)

                # 路径 2: 腾讯源兜底
                if df is None or df.empty:
                    logger.info(f"DEBUG: AkShare native failed, attempting Tencent hist for A-share {ticker}")
                    df = await self._get_tencent_hist(ticker, num_days=req_days + 50, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: Tencent hist for A-share {ticker} success, len={len(df)}")
                        df = df.sort_values("Date")
                        df.set_index('Date', inplace=True)

                # 路径 3: Direct EM API (最后尝试)
                if df is None or df.empty and end_date:
                    logger.info(f"DEBUG: Tencent failed, attempting Direct EM API for A-share {ticker}")
                    df = await self._get_us_hist_em_direct(ticker, num_days=req_days + 50, end_date=end_date)
                    if df is not None and not df.empty:
                        logger.info(f"DEBUG: Direct EM API for A-share {ticker} success, len={len(df)}")
                        df = df.sort_values("Date")
                        df.set_index('Date', inplace=True)

                if df is None or df.empty:
                    logger.info(f"DEBUG: Hist fetch for A-share {ticker} failed all paths.")
                    return None

            # 最终检查 DataFrame 是否有效且包含足够数据点
            if df is None or df.empty or len(df) < 2:
                return None

            # 构建指标缓存 key
            df_hash_key = f"indicators:{ticker}:{len(df)}:{df['Close'].iloc[-1]:.4f}"

            # 尝试从缓存读取指标
            indicators = None
            try:
                from app.core.redis_client import cache_get, cache_set
                import hashlib
                cache_key = hashlib.md5(df_hash_key.encode()).hexdigest()
                indicators = await cache_get(f"ind:{cache_key}")
            except Exception:
                pass

            if indicators is None:
                # 缓存未命中，计算指标
                indicators = TechnicalIndicators.calculate_all(df)
                # 写入缓存：10 分钟 TTL (指标基于 OHLCV，数据不变则指标不变)
                try:
                    from app.core.redis_client import cache_set
                    await cache_set(f"ind:{cache_key}", indicators, ttl_seconds=600)
                except Exception:
                    pass

            # 将 DataFrame 转换为 bars 列表
            bars = []
            # 确保按时间排序
            df = df.sort_index()
            for date, row in df.iterrows():
                bars.append({
                    "time": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    "open": float(row.get('Open', 0)),
                    "high": float(row.get('High', 0)),
                    "low": float(row.get('Low', 0)),
                    "close": float(row.get('Close', 0)),
                    "volume": float(row.get('Volume', 0))
                })

            return {
                "ticker": ticker,
                "bars": bars,
                "indicators": indicators,
                "metadata": {
                    "count": len(bars),
                    "source": "tencent_hist" if not self._is_us_stock(ticker) else "em_hist"
                }
            }
        except Exception as e:
            logger.error(f"AkShare get_historical_data error for {ticker}: {e}")
            return None

    async def get_valuation_percentiles(self, ticker: str) -> Dict[str, Any]:
        """获取 A 股估值百分位 (PE/PB Percentiles)"""
        if self._is_us_stock(ticker):
            return {} # 美股暂不支持百分位抓取
            
        symbol = self._normalize_symbol(ticker)
        try:
            # 使用乐咕乐股数据源
            def fetch_valuation():
                _tls.bypass_proxy = True
                try:
                    @retry_on_network_error(max_retries=2)
                    def _fetch():
                        return ak.stock_a_lg_indicator(symbol=symbol)
                    df = _fetch()
                    if df is not None and not df.empty:
                        latest = df.iloc[-1]
                        # 估算百分位 (简单实现：在最近 500 个交易日中的位置)
                        # 注意：AkShare 有些版本直接提供 pe_low, pe_high
                        pe_val = float(latest.get('pe', 0))
                        pb_val = float(latest.get('pb', 0))
                        
                        # 计算最近一年的百分位
                        recent_df = df.tail(250)
                        pe_percentile = (recent_df['pe'] < pe_val).mean() * 100
                        pb_percentile = (recent_df['pb'] < pb_val).mean() * 100
                        
                        return {
                            "pe_percentile": round(pe_percentile, 2),
                            "pb_percentile": round(pb_percentile, 2)
                        }
                    return {}
                except: return {}
            
            return await asyncio.get_event_loop().run_in_executor(None, fetch_valuation)
        except: return {}

    async def get_capital_flow(self, ticker: str) -> Dict[str, Any]:
        """获取个股资金流向 (主力净流入)"""
        if self._is_us_stock(ticker):
            return {}
            
        symbol = self._normalize_symbol(ticker)
        try:
            def fetch_flow():
                _tls.bypass_proxy = True
                try:
                    # 获取个股资金流向排名 (东财源)
                    @retry_on_network_error(max_retries=2)
                    def _fetch():
                        return ak.stock_individual_fund_flow_rank(indicator="今日")
                    df = _fetch()
                    if df is not None and not df.empty:
                        row = df[df['代码'] == symbol]
                        if not row.empty:
                            target = row.iloc[0]
                            return {
                                "net_inflow": float(target.get('今日主力净流入-净额', 0))
                            }
                    return {}
                except: return {}
                
            return await asyncio.get_event_loop().run_in_executor(None, fetch_flow)
        except: return {}

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        if self._is_us_stock(ticker): return [] # 美股新闻建议由 TavilyProvider 处理 (RAG 更强)
        try:
            symbol = self._normalize_symbol(ticker)
            @retry_on_network_error(max_retries=2)
            def fetch_news():
                return ak.stock_news_em(symbol=symbol)
            news_df = await self._run_sync(fetch_news)
            import hashlib
            results = []
            for _, row in news_df.head(10).iterrows():
                link = row['新闻链接']
                unique_id = hashlib.md5(link.encode()).hexdigest()
                results.append(ProviderNews(id=f"ak-{unique_id}", title=row['新闻标题'], publisher=row.get('文章来源', '东财'), link=link, publish_time=pd.to_datetime(row['发布时间'])))
            return results
        except: return []

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y", end_date: Optional[str] = None) -> List[Any]:
        try:
            df = None
            if self._is_us_stock(ticker):
                # 兼容性逻辑：判断是否为指数 (Index)
                is_index = ticker.upper() in ["NDX", "IXIC", "SPX", "DJI", ".NDX", ".IXIC", ".INX", ".DJI"]
                if is_index:
                    try:
                        df = await self._get_tencent_hist(ticker, num_days=500, end_date=end_date)
                    except: pass

                if df is None or df.empty:
                    try:
                        # 优先尝试更稳定的 Direct EM Hist 接口 (加长 50d 预热)
                        days_map = {"1mo": 40, "3mo": 100, "6mo": 200, "1y": 300, "5y": 1300}
                        req_days = days_map.get(period, 300)
                        df = await self._get_us_hist_em_direct(ticker, num_days=req_days + 50, end_date=end_date)
                        if df is not None and not df.empty:
                            logger.info(f"🚀 [AkShareProvider] get_ohlcv: Direct EM fetch success for {ticker}, len={len(df)}")
                    except Exception as e:
                        logger.warning(f"⚠️ [AkShareProvider] get_ohlcv: Direct EM fetch failed for {ticker}: {e}")

                if df is None or df.empty:
                    try:
                        # 兜底走原有 EM DF 接口
                        df = await self._get_us_hist_em_df(ticker, end_date=end_date)
                    except: pass

                if df is not None and not df.empty:
                    # 统一列名：新浪接口返回 date, open, high, low, close, volume
                    # 个股接口返回相同，但列名大小写可能不同
                    col_map = {c.lower(): c.capitalize() for c in df.columns}
                    if 'date' in col_map: col_map['date'] = 'Date'
                    df = df.rename(columns=col_map)
            else:
                # A 股改用腾讯源
                df = await self._get_tencent_hist(ticker, num_days=1000, end_date=end_date)
                if df is None or df.empty:
                    # 备选
                    symbol = self._normalize_symbol(ticker)
                    start_str = "19900101"
                    end_str = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")
                    df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
                    if df is not None and not df.empty:
                        df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'})
                        # 如果有 end_date，通常取最后的部分（chunk）
                        if end_date:
                            df = df.tail(250)

            if df is None or df.empty: return []
            
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 关键修复：确保日期唯一且有序，防止前端 K 线图断言失败 (Assertion failed: data must be asc ordered by time)
            df = df.drop_duplicates(subset=['Date']).sort_values('Date')
            
            calc_df = TechnicalIndicators.add_historical_indicators(df)
            
            # 优化 1: 截断历史数据 (保留指标前提下)
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # 如果提供了 end_date，说明是回溯加载，不要按照 period 再截断了
            if not end_date:
                if period == "1mo": start_date = now - timedelta(days=30)
                elif period == "3mo": start_date = now - timedelta(days=90)
                elif period == "6mo": start_date = now - timedelta(days=180)
                elif period == "1y": start_date = now - timedelta(days=365)
                elif period == "5y": start_date = now - timedelta(days=365*5)
                else: start_date = None
                
                if start_date:
                    calc_df = calc_df[calc_df['Date'] >= start_date]
            else:
                # 回溯模式，取最后 250 条（作为分片）
                calc_df = calc_df.tail(250)

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
