from typing import Dict, Type
import re

from app.services.market_providers.base import MarketDataProvider
from app.services.market_providers.yfinance import YFinanceProvider
from app.services.market_providers.alpha_vantage import AlphaVantageProvider
from app.services.market_providers.akshare import AkShareProvider

# 供应商工厂 (Factory Pattern)
# 职责：根据股票代码的特征（如 A 股还是美股）或用户的偏好选择，自动匹配并实例化对应的数据抓取器。
class ProviderFactory:
    # 使用类变量缓存单例对象，避免重复创建实例
    _instances: Dict[str, MarketDataProvider] = {}

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "YFINANCE") -> MarketDataProvider:
        """
        核心分流逻辑：已切换至全量使用 AKSHARE，解决国内服务器访问海外 API 受限问题。
        """
        # 强制使用 AKSHARE (由于国内大环境及 YFinance 受限，暂时全量切换)
        return cls._get_instance("AKSHARE")

    @classmethod
    def _get_instance(cls, source: str) -> MarketDataProvider:
        """
        内部方法：单例模式获取 Provider 实例
        """
        if source not in cls._instances:
            if source == "YFINANCE":
                cls._instances[source] = YFinanceProvider()
            elif source == "ALPHA_VANTAGE":
                cls._instances[source] = AlphaVantageProvider()
            elif source == "AKSHARE":
                cls._instances[source] = AkShareProvider()
            else:
                # 兜底
                cls._instances[source] = YFinanceProvider()
        return cls._instances[source]
