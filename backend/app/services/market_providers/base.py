from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.schemas.market_data import ProviderQuote, ProviderFundamental, ProviderNews, FullMarketData

# 数据提供商抽象基类 (Interface/Abstract Base Class)
# 所有的行情来源（YFinance, AkShare等）都必须继承此类并实现以下方法
# 这体现了设计模式中的“接口隔离”和“多态”原则
class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """
        获取实时报价（最新价、涨跌幅等）
        """
        pass

    @abstractmethod
    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        """
        获取基础面数据（市值、PE、行业信息等）
        """
        pass

    @abstractmethod
    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Any]:
        """
        获取历史 K 线数据，通常用于计算技术指标 (RSI, MACD 等)
        """
        pass

    @abstractmethod
    async def get_news(self, ticker: str) -> List[ProviderNews]:
        """
        获取该股票的最新新闻列表
        """
        pass

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
        """
        可选：在一次 API 调用中获取全量数据（报价+基础面+技术指标+新闻）
        如果子类不实现此方法，默认返回 None，由 Service 层通过 gather 并行调用上述独立方法
        """
        return None
