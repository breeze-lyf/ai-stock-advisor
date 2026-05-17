from typing import Dict, Optional
import logging
import threading
from contextvars import ContextVar

from app.services.integrations.market.market_providers.base import MarketDataProvider
from app.services.integrations.market.market_providers.akshare import AkShareProvider
from app.services.integrations.market.market_providers.yfinance import YFinanceProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """供应商工厂：根据股票代码特征或用户偏好选择数据源。

    修复：使用 ContextVar 存储每请求的数据源配置，避免并发请求互相覆盖。
    """
    _instances: Dict[str, MarketDataProvider] = {}
    _lock = threading.Lock()

    # Per-request data source config via contextvar
    _user_data_source_config: ContextVar[Optional[Dict[str, str]]] = ContextVar(
        "user_data_source_config", default=None
    )

    @classmethod
    def set_user_data_source_config(cls, config: Optional[Dict[str, str]]) -> None:
        """设置当前请求上下文的数据源偏好。"""
        cls._user_data_source_config.set(config)

    @classmethod
    def get_user_data_source_config(cls) -> Optional[Dict[str, str]]:
        return cls._user_data_source_config.get()

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "AUTO") -> MarketDataProvider:
        """
        核心分流逻辑：
        1. 显式模式 (AKSHARE/YFINANCE)：尊重用户选择
        2. 自动模式 (AUTO)：按 contextvar 中的用户配置或默认配置选择
        """
        ticker = ticker.upper().strip()

        is_a_share = ticker.isdigit() and len(ticker) == 6
        is_hk_share = ticker.endswith(".HK") and ticker[:-3].isdigit()
        is_us_share = not is_a_share and not is_hk_share

        source = (preferred_source or "AUTO").upper()
        if source == "YFINANCE":
            return cls._get_instance("YFINANCE")
        if source == "AKSHARE":
            return cls._get_instance("AKSHARE")

        # AUTO 模式：优先使用当前请求上下文的配置
        user_config = cls._user_data_source_config.get()
        if user_config:
            if is_a_share:
                data_source = user_config.get("a_share", "YFINANCE")
            elif is_hk_share:
                data_source = user_config.get("hk_share", "YFINANCE")
            elif is_us_share:
                data_source = user_config.get("us_share", "YFINANCE")
            else:
                data_source = "YFINANCE"
            return cls._get_instance(data_source)

        # 默认：A 股/港股用 AkShare，美股用 YFinance
        if is_a_share or is_hk_share:
            return cls._get_instance("AKSHARE")
        if is_us_share:
            return cls._get_instance("YFINANCE")

        return cls._get_instance("AKSHARE")

    @classmethod
    def _get_instance(cls, source: str) -> MarketDataProvider:
        if source not in cls._instances:
            with cls._lock:
                if source not in cls._instances:
                    if source == "AKSHARE":
                        cls._instances[source] = AkShareProvider()
                    elif source == "YFINANCE":
                        cls._instances[source] = YFinanceProvider()
                    else:
                        cls._instances[source] = AkShareProvider()
        return cls._instances[source]
