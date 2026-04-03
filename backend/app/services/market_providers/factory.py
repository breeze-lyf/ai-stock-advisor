from typing import Dict, Optional
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

    # 用户配置的数据源（运行时动态设置）
    # 格式：{"a_share": "YFINANCE", "hk_share": "YFINANCE", "us_share": "YFINANCE"}
    _user_data_source_config: Optional[Dict[str, str]] = None

    @classmethod
    def set_user_data_source_config(cls, config: Dict[str, str]) -> None:
        """
        设置用户的数据源偏好配置

        Args:
            config: 字典，包含各市场的数据源选择
                   示例：{"a_share": "YFINANCE", "hk_share": "AKSHARE", "us_share": "YFINANCE"}
        """
        cls._user_data_source_config = config

    @classmethod
    def get_user_data_source_config(cls) -> Optional[Dict[str, str]]:
        """获取用户的数据源偏好配置"""
        return cls._user_data_source_config

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "AUTO") -> MarketDataProvider:
        """
        核心分流逻辑：

        1. 显式模式 (AKSHARE/YFINANCE)：尊重用户选择

        2. 自动模式 (AUTO)：
           - 如果有用户配置，按用户配置选择
           - 否则使用默认配置：所有市场都用 YFinance

        股票代码规则：
        - A 股：6 位纯数字 (000001, 600519, 300750)
        - 港股：6 位数字+.HK (00700.HK)
        - 美股：字母代码 (AAPL, NVDA, TSLA)
        """
        ticker = ticker.upper().strip()

        # 判断股票类型
        is_a_share = ticker.isdigit() and len(ticker) == 6
        is_hk_share = ticker.endswith(".HK") and ticker[:-3].isdigit()
        is_us_share = not is_a_share and not is_hk_share

        # 处理显式模式
        source = (preferred_source or "AUTO").upper()
        if source == "YFINANCE":
            return cls._get_instance("YFINANCE")
        if source == "AKSHARE":
            return cls._get_instance("AKSHARE")

        # AUTO 模式：根据用户配置或默认配置选择
        if cls._user_data_source_config:
            # 用户已配置数据源
            if is_a_share:
                data_source = cls._user_data_source_config.get("a_share", "YFINANCE")
            elif is_hk_share:
                data_source = cls._user_data_source_config.get("hk_share", "YFINANCE")
            elif is_us_share:
                data_source = cls._user_data_source_config.get("us_share", "YFINANCE")
            else:
                data_source = "YFINANCE"  # 未识别类型默认 YFINANCE

            return cls._get_instance(data_source)

        # 默认配置：所有市场都用 YFinance
        if is_a_share or is_hk_share or is_us_share:
            return cls._get_instance("YFINANCE")

        # 未识别的类型：回退到 AkShare
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
