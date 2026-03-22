from typing import Dict
import logging

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider
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
        核心分流逻辑（默认关闭 IBKR）：
        1. 默认统一走 AkShare。
        2. 只有 preferred_source 明确指定为 IBKR 且 IBKR_ENABLED=true 时，才尝试 IBKR。
        3. IBKR 不可用时自动回退 AkShare。
        """
        source = (preferred_source or "AKSHARE").upper()
        ibkr_enabled = bool(getattr(settings, "IBKR_ENABLED", False))

        if source == "IBKR" and ibkr_enabled and cls._is_ibkr_available():
            return cls._get_instance("IBKR")

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
            elif source == "AKSHARE":
                cls._instances[source] = AkShareProvider()
            else:
                # 兜底：不再使用 YFinance，统一回退到 AKSHARE
                cls._instances[source] = AkShareProvider()
        return cls._instances[source]
