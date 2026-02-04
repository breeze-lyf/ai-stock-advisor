from typing import Dict, Type
import re

from app.services.market_providers.base import MarketDataProvider
from app.services.market_providers.yfinance import YFinanceProvider
from app.services.market_providers.alpha_vantage import AlphaVantageProvider
from app.services.market_providers.akshare import AkShareProvider

class ProviderFactory:
    _instances: Dict[str, MarketDataProvider] = {}

    @classmethod
    def get_provider(cls, ticker: str, preferred_source: str = "YFINANCE") -> MarketDataProvider:
        """
        Logic to determine best provider:
        - If A-share (digits, or ends in .SH/.SZ), use AkShare.
        - Otherwise use preferred_source or YFinance.
        """
        # A-share detection: 6 digits + Optional .SH/SZ or 6 digits
        is_a_share = re.match(r'^\d{6}(\.(SH|SZ))?$', ticker.upper())
        
        if is_a_share:
            return cls._get_instance("AKSHARE")
        
        # Default logic
        source = preferred_source.upper()
        if source not in ["YFINANCE", "ALPHA_VANTAGE", "AKSHARE"]:
            source = "YFINANCE"
            
        return cls._get_instance(source)

    @classmethod
    def _get_instance(cls, source: str) -> MarketDataProvider:
        if source not in cls._instances:
            if source == "YFINANCE":
                cls._instances[source] = YFinanceProvider()
            elif source == "ALPHA_VANTAGE":
                cls._instances[source] = AlphaVantageProvider()
            elif source == "AKSHARE":
                cls._instances[source] = AkShareProvider()
            else:
                # Fallback
                cls._instances[source] = YFinanceProvider()
        return cls._instances[source]
