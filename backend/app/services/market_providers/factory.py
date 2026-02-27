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
        核心分流逻辑：
        1. 6 位数字代码 -> AkShare (A 股)
        2. 带 .SS 或 .SZ 后缀 -> AkShare (A 股)
        3. 其他 -> YFinance (美股)
        """
        # A 股判断逻辑
        is_cn = (ticker.isdigit() and len(ticker) == 6) or \
                any(suffix in ticker.upper() for suffix in ['.SS', '.SZ'])
        
        if is_cn:
            return cls._get_instance("AKSHARE")
        
        # 美股也引导至 AKSHARE (集成了新浪直连行情，适合国内服务器环境)
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
