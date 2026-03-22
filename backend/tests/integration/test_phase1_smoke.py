from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.main import app
from app.models.user import MembershipTier


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value


class FakeSession:
    def __init__(self, results=None):
        self._results = list(results or [])
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.rollback = AsyncMock()
        self.delete = AsyncMock()
        self.added = []

    async def execute(self, _stmt):
        if not self._results:
            raise AssertionError("Unexpected database execute call in smoke test")
        return FakeScalarResult(self._results.pop(0))

    def add(self, obj):
        self.added.append(obj)


def build_user(**overrides):
    return SimpleNamespace(
        id="user-1",
        email="user@example.com",
        membership_tier=MembershipTier.FREE.value,
        api_key_deepseek=None,
        api_key_siliconflow="encrypted-key",
        api_configs=None,
        fallback_enabled=True,
        preferred_data_source="AKSHARE",
        preferred_ai_model="qwen-3-vl-thinking",
        timezone="Asia/Shanghai",
        theme="light",
        feishu_webhook_url=None,
        enable_price_alerts=True,
        enable_hourly_summary=True,
        enable_daily_report=True,
        enable_macro_alerts=True,
        hashed_password="hashed",
        **overrides,
    )


def clear_overrides():
    app.dependency_overrides.clear()


def test_user_profile_and_settings_smoke():
    user = build_user()
    db = FakeSession()

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)

    response = client.get("/api/user/me")
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"

    response = client.put(
        "/api/user/settings",
        json={"preferred_ai_model": "deepseek-v3", "theme": "dark"},
    )
    assert response.status_code == 200
    assert response.json()["preferred_ai_model"] == "deepseek-v3"
    assert response.json()["theme"] == "dark"
    db.commit.assert_awaited()
    db.refresh.assert_awaited()

    clear_overrides()


def test_test_connection_smoke(monkeypatch):
    from app.api.v1.endpoints import user as user_endpoint

    user = build_user()

    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    from app.services.ai_service import AIService

    monkeypatch.setattr(
        AIService,
        "test_connection",
        AsyncMock(return_value=(True, "连接成功")),
    )

    client = TestClient(app)
    response = client.post(
        "/api/user/test-connection",
        json={"provider": "siliconflow", "api_key": "sk-test", "base_url": "https://example.com/v1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    clear_overrides()


def test_analysis_smoke(monkeypatch):
    from app.api.v1.endpoints import analysis as analysis_endpoint
    from app.application.analysis import analyze_stock as analyze_stock_use_case

    user = build_user()
    stock = SimpleNamespace(
        sector="Technology",
        industry="Semiconductors",
        market_cap=1000000,
        pe_ratio=25.0,
        forward_pe=22.0,
        eps=3.0,
        dividend_yield=0.0,
        beta=1.2,
        fifty_two_week_high=120.0,
        fifty_two_week_low=80.0,
    )
    market_data = SimpleNamespace(
        current_price=101.5,
        change_percent=1.2,
        rsi_14=55.0,
        ma_20=99.0,
        ma_50=95.0,
        ma_200=88.0,
        macd_val=1.0,
        macd_hist=0.5,
        macd_hist_slope=0.1,
        bb_upper=110.0,
        bb_middle=100.0,
        bb_lower=90.0,
        k_line=50.0,
        d_line=48.0,
        j_line=54.0,
        atr_14=2.5,
        adx_14=30.0,
        resistance_1=108.0,
        resistance_2=112.0,
        support_1=97.0,
        support_2=93.0,
        market_status="OPEN",
        pe_percentile=70.0,
        pb_percentile=65.0,
        net_inflow=12345.0,
    )
    portfolio_item = SimpleNamespace(avg_cost=95.0, quantity=10)
    db = FakeSession(results=[0, stock, [], portfolio_item, None, None])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    monkeypatch.setattr(
        analyze_stock_use_case.MarketDataService,
        "get_real_time_data",
        AsyncMock(return_value=market_data),
    )
    monkeypatch.setattr(
        analyze_stock_use_case.MacroService,
        "get_latest_radar",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        analyze_stock_use_case.MacroService,
        "get_latest_news",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        analyze_stock_use_case.AIService,
        "generate_analysis",
        AsyncMock(
            return_value=(
                '{"summary_status":"观察","technical_analysis":"技术面稳定",'
                '"fundamental_news":"基本面中性","action_advice":"继续跟踪",'
                '"immediate_action":"HOLD","target_price":110,"stop_loss_price":96}'
            )
        ),
    )

    client = TestClient(app)
    response = client.post("/api/analysis/NVDA")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["summary_status"] == "观察"
    assert body["is_cached"] is False

    clear_overrides()


def test_macro_radar_smoke(monkeypatch):
    from app.api.v1.endpoints import macro as macro_endpoint

    user = build_user()
    topic = SimpleNamespace(
        title="Fed Watch",
        summary="Rate path remains the key macro driver.",
        heat_score=88.0,
        impact_analysis={"logic": "Rates affect valuation", "beneficiaries": [], "detriments": []},
        source_links=[],
        updated_at=datetime.utcnow(),
    )

    async def override_user():
        return user

    async def override_db():
        return FakeSession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(
        macro_endpoint.MacroService,
        "get_latest_radar",
        AsyncMock(return_value=[topic]),
    )

    client = TestClient(app)
    response = client.get("/api/macro/radar")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Fed Watch"

    clear_overrides()


def test_latest_analysis_smoke():
    user = build_user()
    report = SimpleNamespace(
        ticker="NVDA",
        ai_response_markdown="analysis",
        sentiment_score="82",
        summary_status="偏强",
        risk_level="中",
        technical_analysis="技术面稳定",
        fundamental_news="基本面中性",
        action_advice="102附近",
        investment_horizon="中期",
        confidence_level=0.88,
        immediate_action="HOLD",
        target_price=110.0,
        stop_loss_price=96.0,
        entry_zone=None,
        entry_price_low=None,
        entry_price_high=None,
        rr_ratio="2.00",
        scenario_tags=[],
        thought_process=[],
        model_used="qwen-3-vl-thinking",
        created_at=datetime.utcnow(),
    )
    cache = SimpleNamespace(risk_reward_ratio=2.5)
    db = FakeSession(results=[report, cache])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.get("/api/analysis/NVDA")
    assert response.status_code == 200
    assert response.json()["rr_ratio"] == "2.50"
    assert response.json()["entry_price_low"] == 102.0

    clear_overrides()


def test_analysis_history_smoke():
    user = build_user()
    report = SimpleNamespace(
        ticker="NVDA",
        ai_response_markdown="history-analysis",
        sentiment_score="76",
        summary_status="观察",
        risk_level="中",
        technical_analysis="技术面观察",
        fundamental_news="消息面平稳",
        action_advice="99.5-101.5",
        investment_horizon="短期",
        confidence_level=0.7,
        immediate_action="WATCH",
        target_price=108.0,
        stop_loss_price=95.0,
        entry_zone=None,
        entry_price_low=None,
        entry_price_high=None,
        rr_ratio="1.80",
        scenario_tags=[],
        thought_process=[],
        model_used="qwen-3-vl-thinking",
        created_at=datetime.utcnow(),
        input_context_snapshot={"market_data": {"current_price": 100.2}},
    )
    db = FakeSession(results=[[report]])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.get("/api/analysis/NVDA/history")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["history_price"] == 100.2
    assert body[0]["entry_price_low"] == 99.5
    assert body[0]["entry_price_high"] == 101.5

    clear_overrides()


def test_portfolio_analysis_smoke(monkeypatch):
    from app.application.analysis import analyze_portfolio as analyze_portfolio_use_case

    user = build_user()
    holding = SimpleNamespace(
        ticker="NVDA",
        name="NVIDIA",
        market_value=1200.0,
        pl_percent=12.5,
        sector="Technology",
        risk_reward_ratio=2.1,
        pe_percentile=70.0,
        pb_percentile=66.0,
        net_inflow=5000.0,
    )
    summary = SimpleNamespace(holdings=[holding])
    news_item = SimpleNamespace(ticker="NVDA", title="AI demand stays strong", publisher="MockWire")
    persisted_report = SimpleNamespace(created_at=datetime.utcnow())
    db = FakeSession(results=[[news_item]])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    monkeypatch.setattr(
        analyze_portfolio_use_case.GetPortfolioSummaryUseCase,
        "execute",
        AsyncMock(return_value=summary),
    )
    monkeypatch.setattr(
        analyze_portfolio_use_case.MarketDataService,
        "get_real_time_data",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        analyze_portfolio_use_case.MacroService,
        "get_latest_radar",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        analyze_portfolio_use_case.MacroService,
        "get_latest_news",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        analyze_portfolio_use_case.AIService,
        "generate_portfolio_analysis",
        AsyncMock(
            return_value=(
                '{"health_score":78,"risk_level":"中","summary":"组合稳健",'
                '"diversification_analysis":"分散度尚可","strategic_advice":"继续观察",'
                '"top_risks":["单一行业偏高"],"top_opportunities":["AI链条"],'
                '"detailed_report":"组合当前结构健康。"}'
            )
        ),
    )
    monkeypatch.setattr(
        analyze_portfolio_use_case.AnalyzePortfolioUseCase,
        "_persist_report",
        AsyncMock(return_value=persisted_report),
    )

    client = TestClient(app)
    response = client.post("/api/analysis/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert body["health_score"] == 78
    assert body["summary"] == "组合稳健"

    clear_overrides()


def test_portfolio_summary_smoke():
    user = build_user()
    portfolio = SimpleNamespace(ticker="NVDA", quantity=10, avg_cost=100.0)
    market_cache = SimpleNamespace(
        current_price=110.0,
        change_percent=2.0,
        last_updated=datetime.utcnow(),
        risk_reward_ratio=2.4,
    )
    stock = SimpleNamespace(
        name="NVIDIA",
        sector="Technology",
        industry="Semiconductors",
        market_cap=1000000.0,
    )
    db = FakeSession(results=[[(portfolio, market_cache, stock)]])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.get("/api/portfolio/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["holdings"][0]["ticker"] == "NVDA"
    assert body["holdings"][0]["market_value"] == 1100.0
    assert body["sector_exposure"][0]["sector"] == "Technology"

    clear_overrides()


def test_portfolio_list_smoke():
    user = build_user()
    portfolio = SimpleNamespace(
        ticker="NVDA",
        quantity=10,
        avg_cost=100.0,
        sort_order=1,
        created_at=datetime.utcnow(),
    )
    market_cache = SimpleNamespace(
        current_price=110.0,
        last_updated=datetime.utcnow(),
        pe_percentile=70.0,
        pb_percentile=65.0,
        net_inflow=3200.0,
        rsi_14=56.0,
        ma_20=108.0,
        ma_50=103.0,
        ma_200=90.0,
        macd_val=1.2,
        macd_signal=0.9,
        macd_hist=0.3,
        macd_hist_slope=0.05,
        macd_cross="golden",
        macd_is_new_cross=True,
        bb_upper=115.0,
        bb_middle=109.0,
        bb_lower=103.0,
        atr_14=2.1,
        k_line=55.0,
        d_line=51.0,
        j_line=63.0,
        volume_ma_20=1000000.0,
        volume_ratio=1.1,
        adx_14=25.0,
        pivot_point=109.0,
        resistance_1=112.0,
        resistance_2=116.0,
        support_1=106.0,
        support_2=102.0,
        risk_reward_ratio=2.4,
        change_percent=2.0,
    )
    stock = SimpleNamespace(
        name="NVIDIA",
        sector="Technology",
        industry="Semiconductors",
        market_cap=1000000.0,
        pe_ratio=25.0,
        forward_pe=22.0,
        eps=3.2,
        dividend_yield=0.0,
        beta=1.3,
        fifty_two_week_high=120.0,
        fifty_two_week_low=80.0,
    )
    db = FakeSession(results=[[(portfolio, market_cache, stock)]])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.get("/api/portfolio/")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["ticker"] == "NVDA"
    assert body[0]["market_value"] == 1100.0
    assert body[0]["macd_cross"] == "golden"
    assert body[0]["macd_is_new_cross"] is True

    clear_overrides()


def test_add_portfolio_item_smoke():
    user = build_user()
    fresh_cache = SimpleNamespace(rsi_14=55.0, last_updated=datetime.utcnow())
    db = FakeSession(results=[None, None, fresh_cache])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.post(
        "/api/portfolio/",
        json={"ticker": "NVDA", "quantity": 10, "avg_cost": 100.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["needs_fetch"] is False
    assert len(db.added) == 1
    db.commit.assert_awaited()

    clear_overrides()


def test_delete_portfolio_item_smoke():
    user = build_user()
    item = SimpleNamespace(ticker="NVDA")
    db = FakeSession(results=[item])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.delete("/api/portfolio/NVDA")
    assert response.status_code == 200
    assert response.json()["message"] == "Item deleted"
    db.delete.assert_awaited()
    db.commit.assert_awaited()

    clear_overrides()


def test_reorder_portfolio_smoke():
    user = build_user()
    item = SimpleNamespace(sort_order=1)
    db = FakeSession(results=[item])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.patch("/api/portfolio/reorder", json=[{"ticker": "NVDA", "sort_order": 3}])
    assert response.status_code == 200
    assert response.json()["message"] == "Reorder successful"
    assert item.sort_order == 3
    db.commit.assert_awaited()

    clear_overrides()


def test_refresh_portfolio_stock_smoke(monkeypatch):
    from app.application.portfolio import manage_portfolio as manage_portfolio_use_case

    user = build_user()
    quote = SimpleNamespace(price=111.0, change_percent=1.8)
    data = SimpleNamespace(quote=quote)
    cache = SimpleNamespace(current_price=111.0, change_percent=1.8, rsi_14=54.0, last_updated=datetime.utcnow())
    db = FakeSession(results=[cache, cache])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    monkeypatch.setattr(
        manage_portfolio_use_case.MarketDataService,
        "fetch_market_data",
        AsyncMock(return_value=data),
    )
    monkeypatch.setattr(
        manage_portfolio_use_case.MarketDataService,
        "persist_market_data",
        AsyncMock(return_value=None),
    )

    client = TestClient(app)
    response = client.post("/api/portfolio/NVDA/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "深度刷新成功"

    clear_overrides()


def test_latest_portfolio_analysis_smoke():
    user = build_user()
    report = SimpleNamespace(
        health_score=82.0,
        risk_level="中",
        summary="组合均衡",
        diversification_analysis="分散度较好",
        strategic_advice="维持仓位",
        top_risks=["估值波动"],
        top_opportunities=["科技成长"],
        detailed_report="报告详情",
        model_used="qwen-3-vl-thinking",
        created_at=datetime.utcnow(),
    )
    db = FakeSession(results=[report])

    async def override_user():
        return user

    async def override_db():
        return db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.get("/api/analysis/portfolio")
    assert response.status_code == 200
    assert response.json()["summary"] == "组合均衡"
    assert response.json()["health_score"] == 82

    clear_overrides()
