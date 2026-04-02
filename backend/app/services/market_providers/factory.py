from typing import Dict
import logging
import os

from app.services.market_providers.base import MarketDataProvider
from app.services.market_providers.akshare import AkShareProvider
from app.services.market_providers.yfinance import YFinanceProvider

logger = logging.getLogger(__name__)

# 供应商工厂 (Factory Pattern)
# 职责：根据股票代码的特征（如 A 股还是美股）或用户的偏好选择，自动匹配并实例化对应的数据抓取器。
class ProviderFactory:
    # 使用类变量缓存单例对象，避免重复创建实例
    _instances: Dict[str, MarketDataProvider] = {}

    # 环境标识：用于决定美股数据源
    # IS_SERVER_ENV = True 表示运行在服务器环境（无代理，AkShare 更可靠）
    # IS_SERVER_ENV = False 表示本地环境（有代理，YFinance 更可靠）
    IS_SERVER_ENV = os.getenv("IS_SERVER_ENV", "false").lower() == "true"

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "AUTO") -> MarketDataProvider:
        """
        核心分流逻辑：

        1. 自动模式 (AUTO)：根据股票类型和环境自动选择
           - A 股/港股：固定使用 AkShare（数据最准）
           - 美股：本地环境用 YFinance，服务器环境用 AkShare

        2. 显式模式 (AKSHARE/YFINANCE)：尊重用户选择

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

        # A 股/港股：固定使用 AkShare（数据最准、无延迟）
        if is_a_share or is_hk_share:
            return cls._get_instance("AKSHARE")

        # 美股：根据环境选择
        if is_us_share:
            source = (preferred_source or "AUTO").upper()

            if source == "YFINANCE":
                return cls._get_instance("YFINANCE")
            if source == "AKSHARE":
                return cls._get_instance("AKSHARE")

            # AUTO 模式：根据环境自动选择
            if cls.IS_SERVER_ENV:
                # 服务器环境（如阿里云）：用 AkShare（虽然美股数据不全，但比 Yahoo 被墙好）
                return cls._get_instance("AKSHARE")
            else:
                # 本地环境（有代理）：用 YFinance（美股数据更全）
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
