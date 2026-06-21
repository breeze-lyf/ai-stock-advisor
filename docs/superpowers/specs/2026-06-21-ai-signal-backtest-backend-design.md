# AI 信号回测 — 后端引擎与接口（3a）设计文档

日期：2026-06-21
范围：后端。新增「单股 AI 信号回测引擎」+ 查询接口。前端展示（量化页 + 个股页入口）为子项目 3b，不在本 spec。

> 本文档是「AI 信号 → 量化回测」大方向的子项目 3 的后端部分（3a）。前端部分（3b）依赖本 spec 产出的接口，单独立项。

---

## 1. 背景

`analysis_reports` 表已按交易日稳定积累每只股的 AI 信号（`immediate_action` = 买入/卖出/持有/观望，及 `created_at`、`history_price` 等）。用户希望验证「如果每次都按 AI 信号操作，收益如何」。

现有 `QuantitativeBacktestEngine` 是为多股组合 + 因子策略设计的事件驱动框架，单股全仓场景套用反而别扭。本子项目新写一个轻量单股回测函数，不复用其引擎主体。

## 2. 目标

- 对单只股票，按其 AI 信号序列做「全仓买入 / 清仓卖出」回测。
- 输出收益曲线与核心绩效指标，并明确标注样本数。
- 提供查询接口供前端（3b）消费。

## 3. 设计

### 3.1 回测规则（单股，全仓/清仓）

- 信号来源：`analysis_reports` 中该 ticker 的全部有效报告（`summary_status != '调用失败'`），按 `created_at` 升序。
- 价格来源：`get_ohlcv(ticker, interval="1d", period=...)` 的日线序列（`time`/`close`）。每个信号取其 `created_at` 当日（或之后最近交易日）的收盘价为成交价。
- 动作映射：
  - `immediate_action` 含「买」或「建仓」→ 若当前空仓，全仓买入（用全部可用资金按成交价买入）。
  - 含「卖」或「清仓」或「减」→ 若当前持仓，全部卖出。
  - 含「持有」或「观望」或其他 → 不动作。
- 初始资金：100000（固定，回测是相对收益验证，绝对值不重要）。
- 不计手续费/滑点（单股验证场景从简；后续可加）。
- 回测期末若仍持仓，按最后一根 K 线收盘价市值计入（不强制平仓，标记为「持仓中」）。

### 3.2 输出结构 AISignalBacktestResult

新 dataclass（不复用 `BacktestResult`，字段精简到单股所需）：

```python
@dataclass
class AISignalBacktestResult:
    ticker: str
    sample_count: int          # 有效信号条数 N
    trade_count: int           # 实际成交笔数（买+卖）
    total_return_pct: float    # 总收益率 %
    win_rate: float | None     # 胜率（盈利平仓笔数 / 平仓笔数），无平仓为 None
    profit_factor: float | None # 盈亏比（总盈利 / 总亏损绝对值），无亏损为 None
    max_drawdown_pct: float | None  # 最大回撤 %
    final_holding: bool        # 期末是否仍持仓
    equity_curve: list[dict]   # [{date, equity}] 每个交易日的组合市值
    trades: list[dict]         # [{date, action, price, shares}]
    insufficient_sample: bool  # sample_count < 10
```

### 3.3 引擎实现

新文件 `backend/app/services/domain/quant/ai_signal_backtest.py`：

```python
async def run_ai_signal_backtest(db, ticker: str) -> AISignalBacktestResult
```

逻辑：
1. 查该 ticker 的有效信号序列（升序）。
2. 拉日线 K 线，建 date→close 映射。
3. 逐信号模拟全仓/清仓，记录每笔交易；按交易日推进，记录 equity_curve。
4. 算 total_return / win_rate / profit_factor / max_drawdown。
5. `insufficient_sample = sample_count < 10`。

绩效计算放同文件的纯函数（便于核对），不依赖外部框架。

### 3.4 接口

走现有 AI/数据链路约定的 endpoint 模式（参考 `analysis.py`），新增：

```
GET /api/v1/quant/backtest/{ticker}
  鉴权：get_current_user
  返回：AISignalBacktestResult（Pydantic schema 序列化）
```

注册到量化相关 router（若无 quant router，则按现有 router 组织方式新增 `quant.py` endpoint 文件并挂载）。

## 4. 涉及文件

- 新增 `backend/app/services/domain/quant/ai_signal_backtest.py`：引擎 + dataclass + 纯函数。
- 新增/修改 quant endpoint（`backend/app/api/v1/endpoints/quant.py` 或现有 quant router）：`GET /quant/backtest/{ticker}`。
- 新增对应 Pydantic response schema（`backend/app/schemas/` 下，或随 endpoint 定义）。
- 复用：`SchedulerRepository`/`AnalysisRepository` 取信号；`ProviderFactory.get_provider(...).get_ohlcv` 取 K 线。

## 5. 不做（YAGNI）

- 不做多股组合回测（单股）。
- 不做按建仓价/止损/目标的复杂撮合（只全仓/清仓）。
- 不复用 QuantitativeBacktestEngine 主体。
- 不计手续费/滑点（后续可加）。
- 不做前端（3b）。

## 6. 验证

- 单元：对构造的小信号序列 + 已知价格序列，验证 total_return / win_rate / profit_factor / max_drawdown 计算正确（纯函数可直接断言）。
- 接口：本地 curl `GET /api/v1/quant/backtest/MU`（带 token），返回结构完整、sample_count 与 DB 信号数一致、insufficient_sample 在 N<10 时为 true。
- 边界：无信号的 ticker 返回 sample_count=0、trade_count=0、空 equity_curve，不报错。
