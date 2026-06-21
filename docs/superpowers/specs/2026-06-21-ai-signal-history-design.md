# AI 信号历史展示 设计文档

日期：2026-06-21
范围：升级个股详情页 AI 分析 Tab 中现有的 Truth Tracker 子模块，从「最近 3 张卡片」改为「完整信号历史时间线」，并修正胜负判定逻辑。

> 本文档是「AI 信号 → 量化回测」大方向的第 1 个子项目。后两块（稳定分析频率、AI 信号回测）各自独立立项，不在本 spec 范围。

---

## 1. 背景

个股 AI 分析页内的 `TruthTracker` 子模块（位于 `AIVerdict.tsx`）展示「AI 信号追踪与复盘」。当前实现有两个问题：

1. **只展示最近 3 条**（`analysisHistory.slice(0, 3)`），看不到完整历史。
2. **胜负判定只覆盖「买/卖」两种动作**：`immediate_action` 含「买」则涨为命中、含「卖」则跌为命中，其余动作（持有、观望）落入 `null`，判定不完整。

数据本身完整：`analysis_reports` 表经 `GET /api/v1/analysis/{ticker}/history` 返回，每条含 `created_at`、`immediate_action`、`history_price`、`risk_level`、`confidence_level`。

## 2. 目标

- 展示某只股票的**完整** AI 信号历史（不再截断为 3 条）。
- 展示形态从横排卡片改为**紧凑竖向时间线**，承载更多条目。
- 胜负判定逻辑覆盖**四种动作**（买入/卖出/持有/观望）。
- 风格遵循页面现有规范（中性灰、紧凑），不引入新风格。

## 3. 设计

### 3.1 展示形态：横排 3 卡片 → 紧凑竖向时间线

每行一条信号，列：
- 日期（`created_at`，格式 `MMM dd, yyyy`）
- 动作（`immediate_action`，按动作着色：买入=绿、卖出=红、持有=中性、观望=灰）
- 当时价（`history_price`，缺失显示 `--`）
- 至今表现（盈亏百分比，见 3.2）
- 命中/回撤标记（见 3.2）

容器、字号、间距、配色沿用 AIVerdict 现有子模块规范。展示**全部** `analysisHistory`（去掉 `.slice(0,3)`）。

### 3.2 胜负判定：修正动作逻辑（现价回算口径不变）

盈亏仍按现价简单回算（数据现成，不拉历史 K 线）：
```
pl = history_price ? (current_price - history_price) / history_price * 100 : null
```

命中/回撤判定按 `immediate_action` 关键字覆盖四类：

| 动作（关键字） | 判定 |
|------|------|
| 含「买」 | pl > 0 → 命中；pl ≤ 0 → 回撤 |
| 含「卖」或「减」 | pl < 0 → 命中（避开下跌）；pl ≥ 0 → 回撤 |
| 含「持有」 | 同「买」逻辑（看持有期间涨跌） |
| 含「观望」或其他 | 不判定，显示 `--`（无建议动作，无胜负） |

`pl === null`（无 `history_price`）时，表现与命中均显示 `--`。

## 4. 涉及文件

- `frontend/components/features/stock-detail/AIVerdict.tsx`：
  - `TruthTracker` 组件：改展示结构（卡片网格 → 时间线列表）、改判定逻辑（四动作）。
  - 去掉 `analysisHistory.slice(0, 3)` 限制。
- 不需改后端（接口已返回完整历史）。
- 不需改 `useDashboardStockDetailData`（已拉全量 history）。

## 5. 不做（YAGNI）

- 不改 scheduler 分析频率（第 2 块子项目）。
- 不做按投资周期 / 止损-目标先后触及的真回测（第 3 块子项目）。
- 不拉历史 K 线序列。
- 不为缺失 `history_price` 的老记录补数据（显示 `--`）。
- 不做分页（紧凑时间线可纵向滚动，当前每票 ~13 条，量可控）。

## 6. 验证

- 本地起前端（3001），登录后打开有多条历史的个股（如 MU/GOOGL，DB 中已有十余条）AI 分析 Tab：
  - Truth Tracker 显示全部历史信号，不止 3 条。
  - 时间线每行：日期/动作/当时价/表现/命中标记齐全。
  - 买入/卖出/持有的命中判定正确；观望显示 `--`；无 `history_price` 的行表现显示 `--`。
- `npx tsc --noEmit` 通过；`npm run build` 通过。
