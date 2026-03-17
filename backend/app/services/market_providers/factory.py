from typing import Dict, Type
import re
import logging

from app.services.market_providers.base import MarketDataProvider
from app.services.market_providers.alpha_vantage import AlphaVantageProvider
from app.services.market_providers.akshare import AkShareProvider

logger = logging.getLogger(__name__)

# 供应商工厂 (Factory Pattern)
# 职责：根据股票代码的特征（如 A 股还是美股）或用户的偏好选择，自动匹配并实例化对应的数据抓取器。
class ProviderFactory:
    # 使用类变量缓存单例对象，避免重复创建实例
    _instances: Dict[str, MarketDataProvider] = {}

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "AKSHARE") -> MarketDataProvider:
        """
        核心分流逻辑（升级版）：
        1. 6 位数字代码 或 .SS/.SZ 后缀 -> AkShare (A 股)
        2. 美股/港股 -> 优先 IBKR（如果可用），否则回退到 AkShare
        """
        # A 股判断逻辑
        is_cn = (ticker.isdigit() and len(ticker) == 6) or \
                any(suffix in ticker.upper() for suffix in ['.SS', '.SZ'])

        if is_cn:
            # A 股：始终使用 AkShare（国内直连、数据充分）
            return cls._get_instance("AKSHARE")

        # 非 A 股（美股/港股等）：优先 IBKR，fallback 到 AkShare
        if cls._is_ibkr_available():
            return cls._get_instance("IBKR")

        # IBKR 不可用时回退到 AkShare
        return cls._get_instance("AKSHARE")

    @classmethod
    def _is_ibkr_available(cls) -> bool:
        """检查 IBKR Provider 是否可用（不建立真实连接，仅检查配置和库依赖）"""
        try:
            from app.services.market_providers.ibkr import IBKRProvider
            return IBKRProvider.is_available()
        except ImportError:
            return False

    @classmethod
    def _get_instance(cls, source: str) -> MarketDataProvider:
        """
        内部方法：单例模式获取 Provider 实例
        """
        if source not in cls._instances:
            if source == "IBKR":
                from app.services.market_providers.ibkr import IBKRProvider
                cls._instances[source] = IBKRProvider()
            elif source == "ALPHA_VANTAGE":
                cls._instances[source] = AlphaVantageProvider()
            elif source == "AKSHARE":
                cls._instances[source] = AkShareProvider()
            else:
                # 兜底：不再使用 YFinance，统一回退到 AKSHARE
                cls._instances[source] = AkShareProvider()
        return cls._instances[source]
