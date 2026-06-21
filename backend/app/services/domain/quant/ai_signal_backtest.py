"""单股 AI 信号回测：按 immediate_action 全仓买入/清仓卖出，输出绩效。"""
from __future__ import annotations

from dataclasses import dataclass, field

INITIAL_CAPITAL = 100000.0


@dataclass
class AISignalBacktestResult:
    ticker: str
    sample_count: int
    trade_count: int
    total_return_pct: float
    win_rate: float | None
    profit_factor: float | None
    max_drawdown_pct: float | None
    final_holding: bool
    equity_curve: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    insufficient_sample: bool = False


def _is_buy(action: str) -> bool:
    return ("买" in action) or ("建仓" in action)


def _is_sell(action: str) -> bool:
    return ("卖" in action) or ("清仓" in action) or ("减" in action)


def _price_on_or_after(date_str: str, price_map: dict[str, float], sorted_dates: list[str]) -> float | None:
    if date_str in price_map:
        return price_map[date_str]
    for d in sorted_dates:
        if d >= date_str and d in price_map:
            return price_map[d]
    return None


def simulate_ai_signal_backtest(
    ticker: str,
    signals: list[dict],
    price_map: dict[str, float],
    sorted_dates: list[str],
) -> AISignalBacktestResult:
    sample_count = len(signals)
    cash = INITIAL_CAPITAL
    shares = 0.0
    entry_price: float | None = None
    trades: list[dict] = []
    closed_pnls: list[float] = []  # 每笔平仓的盈亏金额

    # 按信号日期映射成交价并执行
    for sig in signals:
        action = sig.get("action") or ""
        price = _price_on_or_after(sig["date"], price_map, sorted_dates)
        if price is None or price <= 0:
            continue
        if _is_buy(action) and shares == 0.0:
            shares = cash / price
            entry_price = price
            cash = 0.0
            trades.append({"date": sig["date"], "action": "买入", "price": price, "shares": round(shares, 4)})
        elif _is_sell(action) and shares > 0.0:
            proceeds = shares * price
            if entry_price is not None:
                closed_pnls.append((price - entry_price) * shares)
            cash = proceeds
            trades.append({"date": sig["date"], "action": "卖出", "price": price, "shares": round(shares, 4)})
            shares = 0.0
            entry_price = None

    # 资金曲线：逐交易日按当日收盘计市值（持仓期间）
    equity_curve: list[dict] = []
    # 用 trades 重放更简单：按 sorted_dates 推进，维护当日持仓状态
    # 重新模拟一次仅为生成曲线（保持与上面成交一致）
    cash2 = INITIAL_CAPITAL
    shares2 = 0.0
    trade_by_date: dict[str, dict] = {t["date"]: t for t in trades}
    for d in sorted_dates:
        t = trade_by_date.get(d)
        close = price_map.get(d)
        if t is not None and close:
            if t["action"] == "买入":
                shares2 = cash2 / close
                cash2 = 0.0
            elif t["action"] == "卖出":
                cash2 = shares2 * close
                shares2 = 0.0
        equity = cash2 + (shares2 * close if (shares2 > 0 and close) else 0.0)
        if close:
            equity_curve.append({"date": d, "equity": round(equity, 2)})

    final_holding = shares > 0.0
    # 期末市值
    last_close = None
    for d in reversed(sorted_dates):
        if d in price_map:
            last_close = price_map[d]
            break
    final_value = cash + (shares * last_close if (final_holding and last_close) else 0.0)
    total_return_pct = round((final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 4)

    # 胜率 / 盈亏比（基于已平仓笔）
    if closed_pnls:
        wins = [p for p in closed_pnls if p > 0]
        losses = [p for p in closed_pnls if p < 0]
        win_rate = round(len(wins) / len(closed_pnls), 4)
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = round(gross_win / gross_loss, 4) if gross_loss > 0 else None
    else:
        win_rate = None
        profit_factor = None

    # 最大回撤
    max_drawdown_pct: float | None = None
    if equity_curve:
        peak = equity_curve[0]["equity"]
        mdd = 0.0
        for pt in equity_curve:
            peak = max(peak, pt["equity"])
            if peak > 0:
                mdd = min(mdd, (pt["equity"] - peak) / peak)
        max_drawdown_pct = round(mdd * 100, 4)

    return AISignalBacktestResult(
        ticker=ticker,
        sample_count=sample_count,
        trade_count=len(trades),
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown_pct=max_drawdown_pct,
        final_holding=final_holding,
        equity_curve=equity_curve,
        trades=trades,
        insufficient_sample=sample_count < 10,
    )
