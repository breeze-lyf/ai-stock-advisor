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

# 线程本地变量，用于在 A 股抓取线程中标记是否停用代理
_tls = threading.local()

# 备份原始 requests.utils.get_environ_proxies
_original_get_environ_proxies = requests.utils.get_environ_proxies

def _patched_get_environ_proxies(url):
    """
    monkey-patch 函数，针对标记了 bypass_proxy 的线程返回空代理。
    """
    if getattr(_tls, 'bypass_proxy', False):
        return {}
    return _original_get_environ_proxies(url)

# 应用全局 patch：通过 TLS 隔离逻辑实现线程级安全禁用代理
requests.utils.get_environ_proxies = _patched_get_environ_proxies

logger = logging.getLogger(__name__)

class AkShareProvider(MarketDataProvider):
    async def _run_sync(self, func, *args, **kwargs):
        """
        在线程池中运行同步函数。
        通过 TLS (Thread Local Storage) 标记当前线程禁用所有代理。
        """
        def run_isolated():
            # 标记当前线程：requests 在调用时会自动触发我们的 patch 函数返回空代理
            _tls.bypass_proxy = True
            
            # 同时也彻底清除环境变量作为双重保险
            old_http = os.environ.get('HTTP_PROXY')
            old_https = os.environ.get('HTTPS_PROXY')
            old_all = os.environ.get('ALL_PROXY')
            
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
                if var in os.environ:
                    del os.environ[var]
            
            try:
                return func(*args, **kwargs)
            finally:
                # 清除标记并恢复环境
                _tls.bypass_proxy = False
                if old_http: os.environ['HTTP_PROXY'] = old_http
                if old_https: os.environ['HTTPS_PROXY'] = old_https
                if old_all: os.environ['ALL_PROXY'] = old_all

        loop = asyncio.get_loop() if hasattr(asyncio, 'get_loop') else asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_isolated)

    def _normalize_symbol(self, ticker: str) -> str:
        """移除后缀并统一代码格式"""
        return ticker.split('.')[0] if '.' in ticker else ticker

    def _get_sina_symbol(self, ticker: str) -> str:
        """转换代码为新浪格式 (如 sz002970, sh600000)"""
        symbol = self._normalize_symbol(ticker)
        if symbol.startswith(('60', '68', '11')): return f"sh{symbol}"
        if symbol.startswith(('00', '30', '12')): return f"sz{symbol}"
        return symbol

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """
        获取 A 股行情。优先使用东财实时快照，确保获取到正确的中文名称。
        """
        symbol = self._normalize_symbol(ticker)
        try:
            # --- 1. 优先方案：东财全市场实时快照 (EM Spot) ---
            # 这种方式最稳，因为它一次性返回名称、价格、涨跌幅
            try:
                spot_df = await self._run_sync(ak.stock_zh_a_spot_em)
                if spot_df is not None and not spot_df.empty:
                    # 匹配代码
                    row = spot_df[spot_df['代码'] == symbol]
                    if not row.empty:
                        target = row.iloc[0]
                        return ProviderQuote(
                            ticker=ticker,
                            price=float(target['最新价']),
                            change=float(target['涨跌额']),
                            change_percent=float(target['涨跌幅']),
                            name=str(target['名称']),
                            market_status=MarketStatus.OPEN,
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.debug(f"AkShare spot_em failed for {ticker}: {e}")

            # --- 2. 回退方案：东财个股详情 ---
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    if '最新' in data and data['最新'] != '-':
                        # 尝试获取涨跌额和涨跌幅
                        change = 0.0
                        change_percent = 0.0
                        try:
                            if '涨跌额' in data and data['涨跌额'] != '-':
                                change = float(data['涨跌额'])
                            if '涨跌幅' in data and data['涨跌幅'] != '-':
                                change_percent = float(data['涨跌幅'])
                        except: pass

                        return ProviderQuote(
                            ticker=ticker,
                            price=float(data['最新']),
                            change=change,
                            change_percent=change_percent,
                            name=data.get('股票简称', ticker),
                            market_status=MarketStatus.OPEN,
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.debug(f"AkShare individual_info_em failed for {ticker}: {e}")

            # --- 3. 备选方案：新浪实时 (Sina Spot) ---
            # 新浪接口通常在 Eastmoney 受限时仍能工作
            try:
                sina_df = await self._run_sync(ak.stock_zh_a_spot)
                if sina_df is not None and not sina_df.empty:
                    sina_symbol = self._get_sina_symbol(ticker)
                    row = sina_df[sina_df['代码'] == sina_symbol]
                    if row.empty:
                        # 兜底匹配：只匹配数字部分
                        row = sina_df[sina_df['代码'].str.contains(symbol)]
                    
                    if not row.empty:
                        target = row.iloc[0]
                        return ProviderQuote(
                            ticker=ticker,
                            price=float(target['最新价']),
                            change=float(target.get('涨跌额', 0.0)),
                            change_percent=float(target.get('涨跌幅', 0.0)),
                            name=str(target['名称']),
                            market_status=MarketStatus.OPEN,
                            last_updated=datetime.utcnow()
                        )
            except Exception as e:
                logger.warning(f"AkShare Sina spot fallback failed for {ticker}: {e}")

            # --- 4. 最终兜底：利用历史 K 线 (计算涨跌辐) ---
            try:
                ohlcv = await self.get_ohlcv(ticker, period="1y")
                if len(ohlcv) >= 2:
                    current = ohlcv[-1]
                    previous = ohlcv[-2]
                    change = current.close - previous.close
                    change_percent = (change / previous.close * 100) if previous.close != 0 else 0.0
                    
                    return ProviderQuote(
                        ticker=ticker,
                        price=current.close,
                        change=change,
                        change_percent=change_percent,
                        name=ticker, 
                        market_status=MarketStatus.OPEN,
                        last_updated=datetime.utcnow()
                    )
                elif ohlcv:
                    last_bar = ohlcv[-1]
                    return ProviderQuote(
                        ticker=ticker,
                        price=last_bar.close,
                        change=0.0,
                        change_percent=0.0,
                        name=ticker,
                        market_status=MarketStatus.OPEN,
                        last_updated=datetime.utcnow()
                    )
            except Exception as e:
                logger.error(f"AkShare get_quote complete blackout for {ticker}: {e}")

            return None
        except Exception as e:
            logger.error(f"AkShare get_quote unexpected error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        try:
            symbol = self._normalize_symbol(ticker)
            
            # 1. 基础信息 (行业, 市值) - 尝试东财，失败则留空
            market_cap = None
            sector = None
            try:
                info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
                if info_df is not None and not info_df.empty:
                    data = {row['item']: row['value'] for _, row in info_df.iterrows()}
                    sector = data.get('行业')
                    if data.get('总市值'):
                        try:
                            market_cap = float(data.get('总市值'))
                        except: pass
            except Exception as e:
                logger.debug(f"Fundamental info_em failed for {ticker}: {e}")
            
            # 2. 每股收益 (EPS) - 尝试同花顺
            eps = None
            try:
                ths_df = await self._run_sync(ak.stock_financial_abstract_ths, symbol=symbol)
                if ths_df is not None and not ths_df.empty:
                    # 获取最新的一条报告数据
                    latest_report = ths_df.iloc[-1]
                    eps_str = str(latest_report.get('基本每股收益', ''))
                    import re
                    match = re.search(r"[-+]?\d*\.\d+|\d+", eps_str)
                    if match:
                        eps = float(match.group())
            except Exception as e:
                logger.debug(f"EPS fetch failed for {ticker}: {e}")
            
            # 3. 52 周高低点 - 来自历史数据回溯 (复用 get_ohlcv 以提高缓存利用率)
            fifty_two_week_high = None
            fifty_two_week_low = None
            try:
                ohlcv = await self.get_ohlcv(ticker, period="1y")
                if ohlcv:
                    prices = [item.close for item in ohlcv]
                    fifty_two_week_high = max(prices)
                    fifty_two_week_low = min(prices)
            except Exception:
                pass

            # 4. 市盈率 (PE) - 基于实时股价简单估算 (Price / EPS)
            pe_ratio = None
            try:
                # 尝试从报价中获取价格
                quote = await self.get_quote(ticker)
                if quote and eps and eps > 0:
                    pe_ratio = quote.price / eps
            except Exception:
                pass
            
            return ProviderFundamental(
                sector=sector,
                industry=sector,
                market_cap=market_cap,
                pe_ratio=pe_ratio,
                eps=eps,
                fifty_two_week_high=fifty_two_week_high,
                fifty_two_week_low=fifty_two_week_low
            )
        except Exception as e:
            logger.error(f"AkShare get_fundamental_data catastrophic error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Dict[str, Any]]:
        try:
            symbol = self._normalize_symbol(ticker)
            # 优先尝试东财 (Eastmoney)
            try:
                df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", adjust="qfq")
            except Exception as e:
                logger.warning(f"Eastmoney hist failed for {ticker}, falling back to Sina: {e}")
                df = pd.DataFrame()

            # 如果东财失败，回退到新浪 (Sina)
            if df is None or df.empty:
                sina_symbol = self._get_sina_symbol(ticker)
                df = await self._run_sync(ak.stock_zh_a_daily, symbol=sina_symbol)
                if df is not None and not df.empty:
                    # 新浪数据格式转换
                    df = df.rename(columns={
                        'date': 'Date', 'open': 'Open', 'close': 'Close', 
                        'high': 'High', 'low': 'Low', 'volume': 'Volume'
                    })
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
            else:
                # 东财数据格式转换
                df = df.rename(columns={
                    '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
                    '最高': 'High', '最低': 'Low', '成交量': 'Volume'
                })
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            
            if df is None or df.empty:
                return None
                
            return TechnicalIndicators.calculate_all(df)
        except Exception as e:
            logger.error(f"AkShare get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        try:
            symbol = self._normalize_symbol(ticker)
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

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> List[Any]:
        """获取原始 K 线数据用于图表展示"""
        try:
            symbol = self._normalize_symbol(ticker)
            from datetime import timedelta
            end_date = datetime.now()
            days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650}
            days = days_map.get(period, 365)
            start_date = end_date - timedelta(days=days)
            
            # 1. 优先尝试东财 (Eastmoney)
            try:
                start_str = start_date.strftime('%Y%m%d')
                end_str = end_date.strftime('%Y%m%d')
                df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", 
                                         start_date=start_str, end_date=end_str, adjust="qfq")
            except Exception:
                df = pd.DataFrame()

            # 2. 如果东财失败，尝试新浪 (Sina)
            if df is None or df.empty:
                sina_symbol = self._get_sina_symbol(ticker)
                df = await self._run_sync(ak.stock_zh_a_daily, symbol=sina_symbol)
                if df is not None and not df.empty:
                    # 过滤日期范围
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                    df = df.rename(columns={
                        'date': '日期', 'open': '开盘', 'close': '收盘',
                        'high': '最高', 'low': '最低', 'volume': '成交量'
                    })

            if df is None or df.empty:
                return []
            
            data = []
            from app.schemas.market_data import OHLCVItem
            for _, row in df.iterrows():
                dt = row['日期'] if '日期' in row else row['Date'] if 'Date' in row else None
                if dt is None: continue
                time_str = dt.strftime('%Y-%m-%d') if not isinstance(dt, str) else str(dt)
                data.append(OHLCVItem(
                    time=time_str,
                    open=float(row['开盘']),
                    high=float(row['最高']),
                    low=float(row['最低']),
                    close=float(row['收盘']),
                    volume=float(row['成交量']) if '成交量' in row else 0.0
                ))
            return data
        except Exception as e:
            logger.error(f"AkShare get_ohlcv error for {ticker}: {e}")
            return []
