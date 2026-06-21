from app.services.domain.quant.ai_signal_backtest import (
    simulate_ai_signal_backtest,
    AISignalBacktestResult,
)


def _dates(*ds):
    return list(ds)


def test_buy_then_sell_profit():
    # 第1天买入(价10)，第3天卖出(价12) → +20%
    dates = _dates("2026-01-01", "2026-01-02", "2026-01-03")
    prices = {"2026-01-01": 10.0, "2026-01-02": 11.0, "2026-01-03": 12.0}
    signals = [
        {"date": "2026-01-01", "action": "买入"},
        {"date": "2026-01-03", "action": "卖出清仓"},
    ]
    r = simulate_ai_signal_backtest("MU", signals, prices, dates)
    assert r.ticker == "MU"
    assert r.sample_count == 2
    assert r.trade_count == 2
    assert round(r.total_return_pct, 2) == 20.0
    assert r.win_rate == 1.0
    assert r.final_holding is False
    assert r.insufficient_sample is True  # 2 < 10


def test_hold_and_watch_no_action():
    dates = _dates("2026-01-01", "2026-01-02")
    prices = {"2026-01-01": 10.0, "2026-01-02": 11.0}
    signals = [
        {"date": "2026-01-01", "action": "持有"},
        {"date": "2026-01-02", "action": "观望"},
    ]
    r = simulate_ai_signal_backtest("MU", signals, prices, dates)
    assert r.trade_count == 0
    assert r.total_return_pct == 0.0
    assert r.win_rate is None  # 无平仓


def test_buy_unrealized_final_holding():
    # 买入未卖，期末持仓按最后收盘计市值
    dates = _dates("2026-01-01", "2026-01-02")
    prices = {"2026-01-01": 10.0, "2026-01-02": 13.0}
    signals = [{"date": "2026-01-01", "action": "建仓"}]
    r = simulate_ai_signal_backtest("MU", signals, prices, dates)
    assert r.trade_count == 1
    assert r.final_holding is True
    assert round(r.total_return_pct, 2) == 30.0


def test_empty_signals():
    r = simulate_ai_signal_backtest("MU", [], {}, [])
    assert r.sample_count == 0
    assert r.trade_count == 0
    assert r.total_return_pct == 0.0
    assert r.equity_curve == []


def test_loss_and_profit_factor():
    # 两笔：第一笔亏(10→9)，第二笔盈(9→12)。profit_factor = 盈利/亏损绝对值
    dates = _dates("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04")
    prices = {"2026-01-01": 10.0, "2026-01-02": 9.0, "2026-01-03": 9.0, "2026-01-04": 12.0}
    signals = [
        {"date": "2026-01-01", "action": "买入"},
        {"date": "2026-01-02", "action": "卖出"},
        {"date": "2026-01-03", "action": "买入"},
        {"date": "2026-01-04", "action": "清仓"},
    ]
    r = simulate_ai_signal_backtest("MU", signals, prices, dates)
    assert r.trade_count == 4
    assert r.win_rate == 0.5
    assert r.profit_factor is not None and r.profit_factor > 1.0
