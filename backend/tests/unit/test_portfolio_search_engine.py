from types import SimpleNamespace

import pytest

from app.application.portfolio.search_engine import PortfolioSearchEngine


class DummyRepo:
    def __init__(self):
        self.stocks = {}
        self.added = []

    async def search(self, query: str, limit: int = 10):
        query_lower = query.lower()
        return [
            stock
            for stock in self.stocks.values()
            if query_lower in stock.ticker.lower() or query_lower in stock.name.lower()
        ][:limit]

    async def get_stock(self, ticker: str):
        return self.stocks.get(ticker)

    async def add_stock_with_cache(self, ticker: str, name: str, current_price: float | None = None):
        stock = SimpleNamespace(ticker=ticker, name=name, current_price=current_price)
        self.stocks[ticker] = stock
        self.added.append(stock)
        return stock


class DummyProvider:
    def __init__(self, quotes=None, instruments=None):
        self.quotes = quotes or {}
        self.instruments = instruments or []

    async def get_quote(self, ticker: str):
        return self.quotes.get(ticker)

    async def search_instruments(self, query: str, limit: int = 10):
        return self.instruments[:limit]


@pytest.mark.asyncio
async def test_search_engine_persists_remote_name_results(monkeypatch):
    from app.application.portfolio import search_engine as module

    repo = DummyRepo()
    provider = DummyProvider(
        instruments=[
            {"ticker": "AAPL", "name": "Apple Inc."},
            {"ticker": "ASTS", "name": "AST SpaceMobile"},
        ]
    )

    monkeypatch.setattr(module, "build_provider_order", lambda preferred, query=None: ["AKSHARE"])
    monkeypatch.setattr(module.ProviderFactory, "get_provider", lambda ticker, preferred_source=None: provider)

    results = await PortfolioSearchEngine(repo).search("apple", preferred_source="AKSHARE", remote=True, limit=10)

    assert [item.ticker for item in results] == ["AAPL", "ASTS"]
    assert repo.stocks["AAPL"].name == "Apple Inc."


@pytest.mark.asyncio
async def test_search_engine_prefers_exact_quote_candidate(monkeypatch):
    from app.application.portfolio import search_engine as module

    repo = DummyRepo()
    provider = DummyProvider(
        quotes={
            "0700.HK": SimpleNamespace(ticker="0700.HK", name="腾讯控股", price=512.0),
        }
    )

    monkeypatch.setattr(module, "build_provider_order", lambda preferred, query=None: ["AKSHARE"])
    monkeypatch.setattr(module.ProviderFactory, "get_provider", lambda ticker, preferred_source=None: provider)

    results = await PortfolioSearchEngine(repo).search("700", preferred_source="AKSHARE", remote=True, limit=10)

    assert results[0].ticker == "0700.HK"
    assert repo.stocks["0700.HK"].name == "腾讯控股"
