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
    def get_provider(cls, ticker: str, preferred_source: str = "AUTO") -> MarketDataProvider:
        """
        核心分流逻辑：

        1. 自动模式 (AUTO)：根据股票类型自动选择
           - A 股/港股：固定使用 AkShare（数据最准）
           - 美股：固定使用 YFinance（数据更全），通过 Cloudflare Worker 代理解决访问问题

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

        # 美股：默认使用 YFinance（通过 Cloudflare Worker 代理解决访问问题）
        if is_us_share:
            source = (preferred_source or "AUTO").upper()

            if source == "YFINANCE":
                return cls._get_instance("YFINANCE")
            if source == "AKSHARE":
                return cls._get_instance("AKSHARE")

            # AUTO 模式：美股统一使用 YFinance
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
