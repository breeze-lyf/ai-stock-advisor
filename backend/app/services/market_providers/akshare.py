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

logger = logging.getLogger(__name__)

@contextmanager
def no_proxy_env():
    """
    临时禁用所有代理环境变量，并 patch requests 模块以绕过系统代理。
    东方财富 API 需要国内直连，不能走海外代理。
    """
    # 保存并清除代理环境变量
    saved_proxies = {}
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    for var in proxy_vars:
        if var in os.environ:
            saved_proxies[var] = os.environ.pop(var)
    
    # 设置 NO_PROXY 为所有东方财富域名
    os.environ['NO_PROXY'] = '*.eastmoney.com,eastmoney.com,push2.eastmoney.com,push2his.eastmoney.com'
    os.environ['no_proxy'] = os.environ['NO_PROXY']
    
    # Patch requests.Session 默认不信任环境/系统代理
    original_init = requests.Session.__init__
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.trust_env = False
        self.proxies = {'http': None, 'https': None}
    
    requests.Session.__init__ = patched_init
    
    try:
        yield
    finally:
        # 恢复 requests.Session
        requests.Session.__init__ = original_init
        
        # 清除 NO_PROXY
        os.environ.pop('NO_PROXY', None)
        os.environ.pop('no_proxy', None)
        
        # 恢复代理环境变量
        for var, value in saved_proxies.items():
            os.environ[var] = value

class AkShareProvider(MarketDataProvider):
    async def _run_sync(self, func, *args, **kwargs):
        """
        在线程池中运行同步函数，并临时禁用代理。
        东方财富 API 只能从国内访问，不能走海外代理。
        """
        def run_without_proxy():
            with no_proxy_env():
                return func(*args, **kwargs)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_without_proxy)

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
            
            # 1. 基础信息 (行业, 市值) - 来自东财
            info_df = await self._run_sync(ak.stock_individual_info_em, symbol=symbol)
            data = {row['item']: row['value'] for _, row in info_df.iterrows()}
            
            # 2. 每股收益 (EPS) - 来自同花顺
            eps = None
            try:
                ths_df = await self._run_sync(ak.stock_financial_abstract_ths, symbol=symbol)
                if not ths_df.empty:
                    # 获取最新的一条报告数据
                    latest_report = ths_df.iloc[-1]
                    eps_str = str(latest_report.get('基本每股收益', ''))
                    import re
                    match = re.search(r"[-+]?\d*\.\d+|\d+", eps_str)
                    if match:
                        eps = float(match.group())
            except Exception as e:
                logger.warning(f"AkShare THS EPS fetch failed for {ticker}: {e}")

            # 3. 52 周高低点 - 来自历史数据回溯
            fifty_two_week_high = None
            fifty_two_week_low = None
            try:
                # 获取过去 1 年的历史数据
                hist_data = await self.get_ohlcv(ticker, period="1y")
                if hist_data:
                    prices = [item.close for item in hist_data]
                    fifty_two_week_high = max(prices)
                    fifty_two_week_low = min(prices)
            except Exception as e:
                logger.warning(f"AkShare 52W High/Low calculation failed for {ticker}: {e}")

            # 4. 市盈率 (PE) - 基于实时股价计算 (Price / EPS)
            pe_ratio = None
            try:
                # 注意：这里不再重复调用 get_quote，因为 MarketDataService 会并发获取 quote 和 fundamental
                # 我们尽量在此处只抓取基础面核心数据。
                # 如果确实需要实时计算 PE，可以在 get_fundamental_data 外部由 MarketDataService 统一处理
                # 或者作为可选注入。为了保持简单，我们这里还是尝试快速拿一下，如果失败也没关系。
                # 但是为了性能，我们优先检查 data['最新'] (来自东财 spot)
                price = float(data['最新']) if '最新' in data else None
                
                if price and eps and eps > 0:
                    pe_ratio = price / eps
            except Exception as e:
                logger.warning(f"AkShare PE calculation failed for {ticker}: {e}")
            
            return ProviderFundamental(
                sector=data.get('行业'),
                industry=data.get('行业'),
                market_cap=float(data.get('总市值', 0)) if data.get('总市值') else None,
                pe_ratio=pe_ratio,
                eps=eps,
                fifty_two_week_high=fifty_two_week_high,
                fifty_two_week_low=fifty_two_week_low
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

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> List[Any]:
        """获取原始 K 线数据用于图表展示"""
        try:
            symbol = ticker.split('.')[0] if '.' in ticker else ticker
            # 对于 A 股，按天获取历史数据
            # AkShare 的 stock_zh_a_hist 并不支持 yfinance 样式的 period 参数，
            # 我们需要手动计算开始日期
            from datetime import timedelta
            end_date = datetime.now()
            
            # 简单的 period 到天数的映射
            days_map = {
                "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 3650
            }
            days = days_map.get(period, 365)
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            df = await self._run_sync(ak.stock_zh_a_hist, symbol=symbol, period="daily", 
                                     start_date=start_str, end_date=end_str, adjust="qfq")
            
            if df.empty:
                return []
            
            data = []
            from app.schemas.market_data import OHLCVItem
            for _, row in df.iterrows():
                data.append(OHLCVItem(
                    time=str(row['日期']),
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
