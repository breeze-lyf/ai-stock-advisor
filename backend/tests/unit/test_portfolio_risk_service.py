from types import SimpleNamespace

import pytest

from app.services.domain.portfolio.portfolio_risk import PortfolioRiskService


class DummyExecuteResult:
    def __init__(self, obj):
        self._obj = obj

    def scalars(self):
        return self

    def first(self):
        return self._obj


class DummyDB:
    def __init__(self, stock):
        self.stock = stock

    async def execute(self, _stmt):
        return DummyExecuteResult(self.stock)


def make_holding(*, ticker: str, quantity: float, avg_cost: float, sector: str, price: float, market_cap: float | None = None, beta: float | None = None):
    return SimpleNamespace(
        ticker=ticker,
        quantity=quantity,
        avg_cost=avg_cost,
        stock=SimpleNamespace(
            sector=sector,
            market_cap=market_cap,
            beta=beta,
            market_data=SimpleNamespace(current_price=price),
        ),
    )


@pytest.mark.asyncio
async def test_analyze_position_impact_uses_stock_relationship_data(monkeypatch):
    holdings = [
        make_holding(ticker="GOOGL", quantity=2, avg_cost=150.0, sector="Communication Services", price=180.0, market_cap=2_000_000_000_000, beta=1.05),
        make_holding(ticker="NET", quantity=1, avg_cost=100.0, sector="Technology", price=120.0, market_cap=90_000_000_000, beta=1.20),
    ]
    target_stock = SimpleNamespace(ticker="AAPL", sector="Technology", beta=1.10)

    async def fake_load_holdings(_db, _user_id):
        return holdings

    monkeypatch.setattr(PortfolioRiskService, "_load_holdings", staticmethod(fake_load_holdings))

    result = await PortfolioRiskService.analyze_position_impact(
        DummyDB(target_stock),
        "user-1",
        "AAPL",
        5.0,
    )

    assert result["current_sector_exposure"][0]["sector"] == "Communication Services"
    assert result["current_sector_exposure"][1]["sector"] == "Technology"
    assert result["projected_sector_exposure"][1]["sector"] == "Technology"
    assert result["projected_sector_exposure"][1]["value"] > result["current_sector_exposure"][1]["value"]
    assert result["current_beta"] > 0
    assert result["projected_beta"] > 0


@pytest.mark.asyncio
async def test_analyze_sector_exposure_uses_position_market_value(monkeypatch):
    holdings = [
        make_holding(ticker="GOOGL", quantity=2, avg_cost=150.0, sector="Communication Services", price=180.0),
        make_holding(ticker="NET", quantity=1, avg_cost=100.0, sector="Technology", price=120.0),
        make_holding(ticker="OBS", quantity=0, avg_cost=50.0, sector="Industrials", price=60.0),
    ]

    async def fake_load_holdings(_db, _user_id):
        return holdings

    monkeypatch.setattr(PortfolioRiskService, "_load_holdings", staticmethod(fake_load_holdings))

    result = await PortfolioRiskService.analyze_sector_exposure(object(), "user-1")

    assert result["total_value"] == 480.0
    assert result["sector_breakdown"] == [
        {"sector": "Communication Services", "value": 360.0, "weight": 0.75},
        {"sector": "Technology", "value": 120.0, "weight": 0.25},
    ]
