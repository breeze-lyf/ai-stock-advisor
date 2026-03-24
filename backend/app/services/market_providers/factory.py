from typing import Dict
import logging

from app.services.market_providers.base import MarketDataProvider
from app.services.market_providers.akshare import AkShareProvider
from app.services.market_providers.yfinance import YFinanceProvider

logger = logging.getLogger(__name__)

# 供应商工厂 (Factory Pattern)
# 职责：根据股票代码的特征（如 A 股还是美股）或用户的偏好选择，自动匹配并实例化对应的数据抓取器。
class ProviderFactory:
    # 使用类变量缓存单例对象，避免重复创建实例
    _instances: Dict[str, MarketDataProvider] = {}

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "AKSHARE") -> MarketDataProvider:
        """
        核心分流逻辑：
        1. 用户显式选择 AKSHARE 或 YFINANCE 时，优先尊重用户设置。
        2. 未识别的来源统一回退到 AKSHARE。
        """
        source = (preferred_source or "AKSHARE").upper()
        if source == "YFINANCE":
            return cls._get_instance("YFINANCE")
        return cls._get_instance("AKSHARE")

    @classmethod
    def _get_instance(cls, source: str) -> MarketDataProvider:
        """
        内部方法：单例模式获取 Provider 实例
        """
        if source not in cls._instances:
            if source == "AKSHARE":
                cls._instances[source] = AkShareProvider()
            elif source == "YFINANCE":
                cls._instances[source] = YFinanceProvider()
            else:
                cls._instances[source] = AkShareProvider()
        return cls._instances[source]
