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
        核心分法逻辑：
        - 如果代码是 6 位数字开头（如 600519），判定为 A 股，强制使用 AkShare。
        - 如果是普通代码（如 AAPL），则根据用户在设置中选择的 preferred_source 来决定。
        """
        # A 股正则匹配：6位数字，可选带 .SH 或 .SZ 后缀
        is_a_share = re.match(r'^\d{6}(\.(SH|SZ))?$', ticker.upper())
        
        if is_a_share:
            return cls._get_instance("AKSHARE")
        
        # 默认分发逻辑
        source = preferred_source.upper()
        if source not in ["YFINANCE", "ALPHA_VANTAGE", "AKSHARE"]:
            source = "YFINANCE"
            
        return cls._get_instance(source)

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
