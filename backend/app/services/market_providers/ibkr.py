"""
IBKR TWS/IB Gateway 数据提供商 (Interactive Brokers Data Provider)

职责：通过 TWS API 获取全球市场的实时行情、基本面数据和历史K线。
特点：
  - 数据来源于交易所直连，质量和实时性远优于 yfinance
  - 不依赖公网海外API，适合中国大陆服务器部署
  - 使用 ib_async 库（ib_insync 的社区维护版本）实现异步连接

连接模式：
  - TWS Live: 端口 7496
  - TWS Paper: 端口 7497
  - IB Gateway Live: 端口 4001
  - IB Gateway Paper: 端口 4002
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider
from app.services.indicators import TechnicalIndicators
from app.schemas.market_data import (
    ProviderQuote, ProviderFundamental, ProviderNews,
    ProviderTechnical, FullMarketData, MarketStatus, OHLCVItem
)
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class IBKRProvider(MarketDataProvider):
    """
    IBKR 数据提供商（单例模式）

    通过 ib_async 连接 TWS/IB Gateway，获取实时行情和历史数据。
    所有方法都做了完善的异常捕获和超时控制，确保连接失败时不阻塞主流程。
    """
    _instance: Optional["IBKRProvider"] = None
    _ib = None          # IB 连接实例
    _connected = False  # 连接状态标记
    _lock = None        # 异步锁，防止并发连接

    def __new__(cls) -> "IBKRProvider":
        """单例模式：确保全局只有一个 IBKR 连接实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._lock is None:
            # 延迟初始化锁（避免在模块加载时创建 event loop 依赖）
            try:
                self._lock = asyncio.Lock()
            except RuntimeError:
                self._lock = None

    async def _ensure_connected(self) -> bool:
        """
        确保与 TWS/IB Gateway 的连接处于活跃状态。
        使用异步锁防止多个协程同时尝试连接。
        如果连接失败，返回 False 让调用方走 fallback 逻辑。
        """
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            # 快速检查：如果已连接且连接仍活跃，直接返回
            if self._ib is not None and self._connected:
                try:
                    if self._ib.isConnected():
                        return True
                except Exception:
                    pass
                self._connected = False

            try:
                from ib_async import IB
                if self._ib is None:
                    self._ib = IB()

                host = getattr(settings, 'IBKR_HOST', '127.0.0.1')
                port = getattr(settings, 'IBKR_PORT', 7497)
                client_id = getattr(settings, 'IBKR_CLIENT_ID', 10)

                logger.info(f"正在连接 IBKR TWS/Gateway: {host}:{port} (clientId={client_id})")

                # 连接超时 5 秒，避免长时间阻塞
                await asyncio.wait_for(
                    self._ib.connectAsync(host, port, clientId=client_id),
                    timeout=5.0
                )

                self._connected = True
                logger.info(f"✅ IBKR 连接成功: {host}:{port}")
                return True

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ IBKR 连接超时 (5s)，将使用备用数据源")
                return False
            except ConnectionRefusedError:
                logger.warning(f"⚠️ IBKR TWS/Gateway 未运行或端口配置错误，将使用备用数据源")
                return False
            except Exception as e:
                logger.error(f"❌ IBKR 连接失败: {e}")
                return False

    def _create_contract(self, ticker: str):
        """
        根据 ticker 创建 IBKR Contract 对象。
        支持美股、港股格式识别。

        美股示例：AAPL, MSFT, GOOGL
        港股示例：0700.HK → 700 + SEHK exchange
        """
        from ib_async import Stock as IBStock

        # 港股判断 (0700.HK 格式)
        if ticker.upper().endswith('.HK'):
            hk_code = ticker.replace('.HK', '').replace('.hk', '').lstrip('0')
            return IBStock(hk_code, 'SEHK', 'HKD')

        # 默认美股 (SMART 路由)
        return IBStock(ticker, 'SMART', 'USD')

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """
        获取实时报价：最新价、涨跌幅等。
        使用 reqMktData 快照模式（snapshot=True）避免持续订阅。
        """
        if not await self._ensure_connected():
            return None

        try:
            contract = self._create_contract(ticker)

            # 请求 snapshot 行情（不需要持续订阅）
            # qualifyContracts 确保合约有效
            qualified = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(contract),
                timeout=5.0
            )
            if not qualified:
                logger.warning(f"IBKR 无法识别合约: {ticker}")
                return None

            contract = qualified[0]

            # 请求快照行情数据
            ticker_data = self._ib.reqMktData(contract, snapshot=True)

            # 等待数据就绪（最多 5 秒）
            for _ in range(50):
                await asyncio.sleep(0.1)
                if ticker_data.last is not None or ticker_data.close is not None:
                    break

            # 取价格：优先 last，次选 close
            price = None
            if ticker_data.last is not None and ticker_data.last > 0:
                price = float(ticker_data.last)
            elif ticker_data.close is not None and ticker_data.close > 0:
                price = float(ticker_data.close)

            if price is None or price <= 0:
                logger.warning(f"IBKR 未能获取 {ticker} 的有效价格")
                return None

            # 涨跌幅计算
            change_pct = 0.0
            prev_close = ticker_data.close if ticker_data.close and ticker_data.close > 0 else None
            if prev_close and price != prev_close:
                change_pct = ((price - prev_close) / prev_close) * 100

            # 判断市场状态
            market_status = MarketStatus.OPEN
            now = utc_now_naive()
            # 简化判断：UTC 时间 14:30-21:00 为美股交易时间
            if now.hour < 14 or (now.hour == 14 and now.minute < 30) or now.hour >= 21:
                market_status = MarketStatus.CLOSED

            # 取消数据订阅（释放 API 额度）
            self._ib.cancelMktData(contract)

            return ProviderQuote(
                ticker=ticker,
                price=price,
                change=float(price - prev_close) if prev_close else 0.0,
                change_percent=round(change_pct, 2),
                name=contract.symbol,  # IBKR 只返回 symbol，不提供公司全名
                market_status=market_status,
                last_updated=utc_now_naive()
            )

        except asyncio.TimeoutError:
            logger.warning(f"IBKR get_quote 超时: {ticker}")
            return None
        except Exception as e:
            logger.error(f"IBKR get_quote 异常 ({ticker}): {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        """
        获取基本面数据：PE、市值、EPS、Beta 等。

        实现策略：
        1. 优先使用 generic tick 方式（不需要额外订阅）
           - Tick 258: Fundamental Ratios (PE, PB, EPS, etc.)
        2. 如果订阅了 Reuters Fundamental，用 reqFundamentalData 获取更全面的数据
        """
        if not await self._ensure_connected():
            return None

        try:
            contract = self._create_contract(ticker)
            qualified = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(contract),
                timeout=5.0
            )
            if not qualified:
                return None

            contract = qualified[0]

            # 方式一：使用 generic ticks 获取基本面数据
            # 258 = Fundamental Ratios (包含 PE, PB, EPS 等)
            # 104 = Historical Volatility
            # 106 = Implied Volatility
            # 165 = Misc Stats (含 52周高低)
            generic_ticks = "258,104,165"
            ticker_data = self._ib.reqMktData(contract, genericTickList=generic_ticks, snapshot=True)

            # 等待 fundamental ratios 数据就绪
            await asyncio.sleep(2.0)

            pe_ratio = None
            eps = None
            dividend_yield = None
            market_cap = None
            beta = None
            high_52w = None
            low_52w = None

            # 从 fundamentalRatios 中提取数据（ib_async 会自动解析 tick 258）
            if hasattr(ticker_data, 'fundamentalRatios') and ticker_data.fundamentalRatios:
                ratios = ticker_data.fundamentalRatios
                pe_ratio = getattr(ratios, 'PEEXCLXOR', None) or getattr(ratios, 'APENORM', None)
                eps = getattr(ratios, 'TTMEPSXCLX', None) or getattr(ratios, 'AEPSNORM', None)
                dividend_yield = getattr(ratios, 'YIELD', None)
                # 市值 = 股价 * 总股数
                shares = getattr(ratios, 'MKTCAP', None)
                if shares:
                    market_cap = shares * 1_000_000  # MKTCAP 单位是百万

            # 52周高低
            if ticker_data.high52 is not None:
                high_52w = float(ticker_data.high52)
            if ticker_data.low52 is not None:
                low_52w = float(ticker_data.low52)

            self._ib.cancelMktData(contract)

            # 如果什么数据都没有，返回 None
            if pe_ratio is None and eps is None and market_cap is None:
                logger.info(f"IBKR 未获取到 {ticker} 的基本面数据（可能需要 Reuters 订阅）")
                return None

            return ProviderFundamental(
                pe_ratio=float(pe_ratio) if pe_ratio else None,
                eps=float(eps) if eps else None,
                dividend_yield=float(dividend_yield) / 100 if dividend_yield else None,
                market_cap=float(market_cap) if market_cap else None,
                beta=float(beta) if beta else None,
                fifty_two_week_high=high_52w,
                fifty_two_week_low=low_52w
            )

        except asyncio.TimeoutError:
            logger.warning(f"IBKR get_fundamental_data 超时: {ticker}")
            return None
        except Exception as e:
            logger.error(f"IBKR get_fundamental_data 异常 ({ticker}): {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo", end_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取历史 K 线并计算技术指标 (RSI, MACD, MA, BB, KDJ, ATR 等)。

        使用 reqHistoricalData 获取 OHLCV 数据，然后通过 TechnicalIndicators 类计算全部指标。
        这确保了与 yfinance provider 完全一致的指标计算结果。
        """
        if not await self._ensure_connected():
            return None

        try:
            contract = self._create_contract(ticker)
            qualified = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(contract),
                timeout=5.0
            )
            if not qualified:
                return None

            contract = qualified[0]

            # 将 period 参数映射到 IBKR 的 durationStr 格式
            # yfinance 风格: "1mo", "200d", "1y"
            # IBKR 风格:    "1 M",  "200 D", "1 Y"
            duration_map = {
                "1mo": "30 D", "3mo": "90 D", "6mo": "180 D",
                "1y": "1 Y", "2y": "2 Y", "5y": "5 Y",
                "200d": "200 D", "100d": "100 D", "50d": "50 D"
            }
            duration_str = duration_map.get(period, "200 D")

            # 将 interval 参数映射到 IBKR 的 barSizeSetting
            bar_size_map = {
                "1d": "1 day", "1h": "1 hour", "5m": "5 mins",
                "15m": "15 mins", "30m": "30 mins", "1w": "1 week"
            }
            bar_size = bar_size_map.get(interval, "1 day")

            # 转换 end_date 为 IBKR 格式 (YYYYMMDD HH:mm:ss)
            ib_end_date = ""
            if end_date:
                # 假设 end_date 是 YYYY-MM-DD
                ib_end_date = end_date.replace("-", "") + " 23:59:59"

            # 请求历史数据
            bars = await asyncio.wait_for(
                self._ib.reqHistoricalDataAsync(
                    contract,
                    endDateTime=ib_end_date,  # 使用指定的截止时间
                    durationStr=duration_str,
                    barSizeSetting=bar_size,
                    whatToShow='TRADES',
                    useRTH=True,  # 仅正常交易时段
                    formatDate=1
                ),
                timeout=15.0
            )

            if not bars:
                logger.warning(f"IBKR 未返回 {ticker} 的历史数据")
                return None

            # 将 IBKR bars 转换为标准 pandas DataFrame
            # TechnicalIndicators 期望的列名：Close, High, Low, Volume, Open
            df = pd.DataFrame([{
                'Open': bar.open,
                'High': bar.high,
                'Low': bar.low,
                'Close': bar.close,
                'Volume': bar.volume,
                'Date': bar.date
            } for bar in bars])

            if df.empty or len(df) < 10:
                return None

            df.set_index('Date', inplace=True)

            # 复用项目现有的技术指标计算引擎
            indicators = TechnicalIndicators.calculate_all(df)
            return indicators

        except asyncio.TimeoutError:
            logger.warning(f"IBKR get_historical_data 超时: {ticker}")
            return None
        except Exception as e:
            logger.error(f"IBKR get_historical_data 异常 ({ticker}): {e}")
            return None

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y", end_date: Optional[str] = None) -> List[Any]:
        """
        获取原始 K 线数据，用于前端趋势图表展示。
        包含附加计算的技术指标（RSI、MACD、布林带）叠加在每根 K 线上。
        """
        if not await self._ensure_connected():
            return []

        try:
            contract = self._create_contract(ticker)
            qualified = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(contract),
                timeout=5.0
            )
            if not qualified:
                return []

            contract = qualified[0]

            duration_map = {
                "1mo": "30 D", "3mo": "90 D", "6mo": "180 D",
                "1y": "1 Y", "2y": "2 Y", "5y": "5 Y"
            }
            duration_str = duration_map.get(period, "1 Y")

            bar_size_map = {
                "1d": "1 day", "1h": "1 hour", "5m": "5 mins",
                "15m": "15 mins", "30m": "30 mins", "1w": "1 week"
            }
            bar_size = bar_size_map.get(interval, "1 day")

            # 转换 end_date 为 IBKR 格式
            ib_end_date = ""
            if end_date:
                ib_end_date = end_date.replace("-", "") + " 23:59:59"

            bars = await asyncio.wait_for(
                self._ib.reqHistoricalDataAsync(
                    contract,
                    endDateTime=ib_end_date,
                    durationStr=duration_str,
                    barSizeSetting=bar_size,
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=1
                ),
                timeout=15.0
            )

            if not bars:
                return []

            # 构建 DataFrame 用于技术指标计算
            df = pd.DataFrame([{
                'Open': bar.open,
                'High': bar.high,
                'Low': bar.low,
                'Close': bar.close,
                'Volume': bar.volume,
                'Date': bar.date
            } for bar in bars])

            if df.empty:
                return []

            df.set_index('Date', inplace=True)

            # 使用现有引擎添加技术指标列（RSI、MACD、布林带）
            df = TechnicalIndicators.add_historical_indicators(df)

            # 替换 NaN 为 None
            df = df.where(pd.notnull(df), None)

            # 将日期索引转为字符串列
            df['time'] = df.index.astype(str).str[:10]  # 取 YYYY-MM-DD 部分

            records = df.to_dict('records')

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
                    bb_lower=row.get('bb_lower')
                ))

            return data

        except asyncio.TimeoutError:
            logger.warning(f"IBKR get_ohlcv 超时: {ticker}")
            return []
        except Exception as e:
            logger.error(f"IBKR get_ohlcv 异常 ({ticker}): {e}")
            return []

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        """
        IBKR 新闻获取。
        注意：IBKR 的新闻 API 需要额外的数据订阅（如 Dow Jones, Reuters 等）。
        本项目的新闻已通过 Tavily 和 AkShare 覆盖，因此这里返回空列表。
        如果用户订阅了 IBKR 新闻服务，可以在此扩展实现。
        """
        return []

    async def get_valuation_percentiles(self, ticker: str) -> Dict[str, Any]:
        """
        基于历史 PE/PB 数据计算估值百分位。

        实现策略：
        使用 IBKR 的历史数据请求获取近 3 年的 PE 和 价格数据，
        然后通过统计方法计算当前 PE 处于历史多少百分位。

        注意：如果没有 Reuters Fundamental 订阅，此方法可能数据不足。
        此时返回空字典，由上层逻辑决定如何处理。
        """
        # IBKR 的 fundamental ratios tick 只提供当前值，不提供历史序列
        # 需要 Reuters 订阅才能通过 reqFundamentalData 获取历史 PE
        # 暂时返回空字典，后续可以通过存储历史 PE 快照来自行计算
        return {}

    async def get_capital_flow(self, ticker: str) -> Dict[str, Any]:
        """
        资金流数据。
        IBKR 不直接提供资金流（主力/散户）数据。
        返回空字典，由 AkShare 补充覆盖。
        """
        return {}

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
        """
        一次性获取全量数据：报价 + 基本面 + 技术指标。
        通过 asyncio.gather 并行请求，提升性能。
        """
        if not await self._ensure_connected():
            return None

        try:
            # 并行获取三大类数据
            quote_task = self.get_quote(ticker)
            fundamental_task = self.get_fundamental_data(ticker)
            historical_task = self.get_historical_data(ticker, period="200d")

            quote, fundamental, indicators = await asyncio.gather(
                quote_task, fundamental_task, historical_task,
                return_exceptions=True
            )

            # 报价是必须有的，其他可选
            if isinstance(quote, Exception) or not quote:
                return None

            technical = None
            if not isinstance(indicators, Exception) and indicators:
                technical = ProviderTechnical(indicators=indicators)

            fund = None
            if not isinstance(fundamental, Exception) and fundamental:
                fund = fundamental

            return FullMarketData(
                quote=quote,
                fundamental=fund,
                technical=technical,
                news=[]  # 新闻由 Tavily 提供
            )

        except Exception as e:
            logger.error(f"IBKR get_full_data 异常 ({ticker}): {e}")
            return None

    async def disconnect(self) -> None:
        """断开 IBKR 连接（应用关闭时调用）"""
        if self._ib and self._connected:
            try:
                self._ib.disconnect()
                self._connected = False
                logger.info("IBKR 连接已断开")
            except Exception as e:
                logger.error(f"IBKR 断开连接异常: {e}")

    @classmethod
    def is_available(cls) -> bool:
        """
        快速检查 IBKR 是否可用（不建立连接）。
        用于工厂模式中的快速判断。
        """
        enabled = getattr(settings, 'IBKR_ENABLED', False)
        if not enabled:
            return False

        try:
            import ib_async  # noqa: F401
            return True
        except ImportError:
            logger.warning("ib_async 未安装，IBKR Provider 不可用")
            return False
