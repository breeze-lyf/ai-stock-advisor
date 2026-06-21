# AI 信号回测后端（3a）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增「单股 AI 信号回测引擎」纯函数 + 异步数据装配 + 查询接口 `GET /api/v1/quant/backtest/{ticker}`。

**Architecture:** 引擎拆成两层：纯函数 `simulate_ai_signal_backtest(ticker, signals, price_map)` 做全部回测数学（可脱库单测），异步 `run_ai_signal_backtest(db, ticker)` 负责取信号+K线后调纯函数。接口挂到现有 quant_factors router（prefix `/quant`），无需新挂载。

**Tech Stack:** FastAPI / SQLAlchemy async / Python dataclass / pytest

## Global Constraints

- 信号源：`AnalysisRepository.get_report_history_for_ticker(ticker, limit, model_used=None)` 返回 SHARED_SCOPE 报告，**降序**；引擎内须**升序**处理。过滤 `summary_status != "调用失败"`。
- 动作映射：含「买」或「建仓」→空仓则全仓买入；含「卖」或「清仓」或「减」→有仓则清仓；含「持有」「观望」及其他→不动作。
- 价格：`ProviderFactory.get_provider(ticker, "AUTO").get_ohlcv(ticker, interval="1d", period="2y")`，每条 K 线含 `time`(YYYY-MM-DD 字符串) 与 `close`(float)。成交价取信号日期当日收盘；当日无 K 线则取之后最近交易日。
- 初始资金 100000.0；不计手续费/滑点。期末仍持仓则按最后一根 K 线收盘价计市值，`final_holding=True`。
- `insufficient_sample = sample_count < 10`。
- 测试用 pytest，置于 `backend/tests/unit/`，命令在 `backend/` 下 `python3 -m pytest`。
- 提交信息结尾附：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 回测纯函数 + 结果 dataclass

**Files:**
- Create: `backend/app/services/domain/quant/ai_signal_backtest.py`
- Test: `backend/tests/unit/test_ai_signal_backtest.py`

**Interfaces:**
- Produces:
  - `@dataclass AISignalBacktestResult`（字段见下）
  - `simulate_ai_signal_backtest(ticker: str, signals: list[dict], price_map: dict[str, float], sorted_dates: list[str]) -> AISignalBacktestResult`
    - `signals`: 升序，每项 `{"date": "YYYY-MM-DD", "action": str}`
    - `price_map`: `date_str -> close`
    - `sorted_dates`: 升序的全部交易日字符串列表（用于推进 equity_curve 与「之后最近交易日」查找）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/unit/test_ai_signal_backtest.py`：

```python
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
```

- [ ] **Step 2: 运行验证失败**

Run: `cd backend && python3 -m pytest tests/unit/test_ai_signal_backtest.py -v`
Expected: FAIL（模块/函数不存在，ImportError）

- [ ] **Step 3: 实现引擎纯函数**

创建 `backend/app/services/domain/quant/ai_signal_backtest.py`：

```python
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
```

- [ ] **Step 4: 运行验证通过**

Run: `cd backend && python3 -m pytest tests/unit/test_ai_signal_backtest.py -v`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/domain/quant/ai_signal_backtest.py backend/tests/unit/test_ai_signal_backtest.py
git commit -m "feat(quant): 单股 AI 信号回测纯函数 + 单测

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 异步数据装配 run_ai_signal_backtest

**Files:**
- Modify: `backend/app/services/domain/quant/ai_signal_backtest.py`（追加异步函数）

**Interfaces:**
- Consumes: `simulate_ai_signal_backtest`（Task 1）；`AnalysisRepository(db).get_report_history_for_ticker(ticker, limit, model_used=None)`（返回降序 ORM 列表，含 `.created_at`/`.immediate_action`/`.summary_status`）；`ProviderFactory.get_provider(ticker, "AUTO").get_ohlcv(ticker, interval="1d", period="2y")`（返回带 `.time`/`.close` 或 dict 的列表）。
- Produces: `async run_ai_signal_backtest(db, ticker: str) -> AISignalBacktestResult`

- [ ] **Step 1: 追加异步装配函数**

在 `ai_signal_backtest.py` 末尾追加：

```python
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.services.integrations.market.market_providers import ProviderFactory


def _ohlcv_field(item, name):
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


async def run_ai_signal_backtest(db, ticker: str) -> AISignalBacktestResult:
    ticker = ticker.upper().strip()
    repo = AnalysisRepository(db)
    reports = await repo.get_report_history_for_ticker(ticker, limit=500)
    # 过滤失败、升序
    valid = [
        r for r in reports
        if (getattr(r, "summary_status", None) != "调用失败")
        and getattr(r, "immediate_action", None)
        and getattr(r, "created_at", None)
    ]
    valid.sort(key=lambda r: r.created_at)
    signals = [
        {"date": r.created_at.strftime("%Y-%m-%d"), "action": r.immediate_action or ""}
        for r in valid
    ]

    # K 线
    provider = ProviderFactory.get_provider(ticker, "AUTO")
    ohlcv = await provider.get_ohlcv(ticker, interval="1d", period="2y")
    price_map: dict[str, float] = {}
    for item in (ohlcv or []):
        t = _ohlcv_field(item, "time")
        c = _ohlcv_field(item, "close")
        if t and c:
            price_map[str(t)[:10]] = float(c)
    sorted_dates = sorted(price_map.keys())

    return simulate_ai_signal_backtest(ticker, signals, price_map, sorted_dates)
```

- [ ] **Step 2: 冒烟验证（无 DB 单测，确认 import 链可加载）**

Run: `cd backend && python3 -c "from app.services.domain.quant.ai_signal_backtest import run_ai_signal_backtest; print('import ok')"`
Expected: `import ok`（确认追加的 import 不破坏加载）

- [ ] **Step 3: 确认 Task 1 单测仍通过**

Run: `cd backend && python3 -m pytest tests/unit/test_ai_signal_backtest.py -v`
Expected: 6 passed（纯函数不受影响）

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/domain/quant/ai_signal_backtest.py
git commit -m "feat(quant): run_ai_signal_backtest 异步装配信号与K线

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 接口 GET /api/v1/quant/backtest/{ticker}

**Files:**
- Modify: `backend/app/api/v1/endpoints/quant_factors.py`（追加 endpoint）

**Interfaces:**
- Consumes: `run_ai_signal_backtest(db, ticker)`（Task 2）；`get_current_user`、`get_db` 依赖（同文件已有其他 endpoint 的用法）。
- Produces: `GET /api/v1/quant/backtest/{ticker}` → JSON（dataclass 用 `dataclasses.asdict` 序列化）

- [ ] **Step 1: 查看 quant_factors.py 现有依赖导入与 router 用法**

Run: `cd backend && grep -nE "get_current_user|get_db|router = |from app" app/api/v1/endpoints/quant_factors.py | head`
Expected: 看到 `router = APIRouter()` 及 `get_db`/`get_current_user` 导入方式（若缺则在本任务补齐导入）

- [ ] **Step 2: 追加 endpoint**

在 `quant_factors.py` 末尾追加（若文件未导入这些则在顶部补：`from dataclasses import asdict`、`from app.services.domain.quant.ai_signal_backtest import run_ai_signal_backtest`、并确保 `get_db`/`get_current_user`/`AsyncSession`/`User` 已导入）：

```python
@router.get("/backtest/{ticker}")
async def ai_signal_backtest(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单股 AI 信号回测：按历史 immediate_action 全仓买入/清仓卖出，返回绩效。"""
    result = await run_ai_signal_backtest(db, ticker)
    return asdict(result)
```

- [ ] **Step 3: 冒烟验证路由注册（TestClient，伪造鉴权，无真实持仓）**

Run:
```bash
cd backend && python3 -c "
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
class F: id='x'; email='t@t.com'
app.dependency_overrides[get_current_user]=lambda:F()
c=TestClient(app)
r=c.get('/api/v1/quant/backtest/ZZZZ')
print('status', r.status_code)
print('keys', sorted(r.json().keys()) if r.status_code==200 else r.json())
" 2>&1 | grep -vE "INFO|WARNING|Proxy|NO_PROXY|akshare|scheduler|lifespan" | tail -5
```
Expected: `status 200`，`keys` 含 `sample_count`/`total_return_pct`/`equity_curve`/`insufficient_sample` 等（ZZZZ 无信号 → sample_count 0，不报错）

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/v1/endpoints/quant_factors.py
git commit -m "feat(quant): 新增 GET /quant/backtest/{ticker} AI信号回测接口

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 联调验证（真实数据）

**Files:** 无（验证）

- [ ] **Step 1: 全单测**

Run: `cd backend && python3 -m pytest tests/unit/test_ai_signal_backtest.py -v`
Expected: 6 passed

- [ ] **Step 2: 真实 ticker 回测（本地后端在线）**

本地后端（8000）。用 TestClient 直连 DB 跑一只有信号的票（MU）：
```bash
cd backend && python3 -c "
import asyncio
from app.core.database import SessionLocal
from app.services.domain.quant.ai_signal_backtest import run_ai_signal_backtest
async def main():
    async with SessionLocal() as db:
        r = await run_ai_signal_backtest(db, 'MU')
        print('sample', r.sample_count, 'trades', r.trade_count, 'ret%', r.total_return_pct, 'insufficient', r.insufficient_sample)
asyncio.run(main())
" 2>&1 | grep -vE "INFO|WARNING|Proxy|NO_PROXY|akshare|scheduler|lifespan" | tail -3
```
Expected: 打印出 MU 的 sample_count（应与 DB 中 MU 有效信号数接近）、trades、收益率，无异常

- [ ] **Step 3: 无额外提交**

---

## 验证清单（对照 spec）

- spec 3.1 回测规则（全仓/清仓、价格口径、初始资金） → Task 1 纯函数 + Global Constraints ✅
- spec 3.2 输出结构 AISignalBacktestResult → Task 1 ✅
- spec 3.3 引擎实现（纯函数 + 异步装配） → Task 1 + Task 2 ✅
- spec 3.4 接口 GET /quant/backtest/{ticker} → Task 3 ✅
- spec 6 验证（单元 + 接口 + 边界空信号） → Task 1 测试含 empty_signals，Task 3 ZZZZ 边界，Task 4 真实数据 ✅
