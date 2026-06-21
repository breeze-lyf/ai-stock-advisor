# 个股详情页 UI 重构 + 列表拖拽排序 设计文档

日期：2026-06-21
范围：个股详情页「AI 分析」Tab 的板块样式统一、顺序调整、删除重复板块；左侧股票列表拖拽排序。

---

## 1. 背景与问题

GOOGL 等个股的「AI 分析」Tab 由 7 个板块组成，存在三类问题：

1. **样式不一致**：父容器统一 `px-4 md:px-8`，但各板块卡片自带的圆角/内边距/边框色完全没有规范，视觉上「不是一套」。
   - AIVerdict：`rounded-[2rem]`、`px-4 md:px-10`、border-neutral-100
   - PositionOverlay：`rounded-[28px]`、`px-5 md:px-7`、border-neutral-200
   - KeyAssumptions：`rounded-2xl`、无横向 px、border-neutral-100
   - RiskAnalysis：`rounded-xl`、`p-6`、border-neutral-200
   - MultiTimeframeAnalysis：`rounded-xl`、`p-4`、border-neutral-700（偏重）
2. **顺序割裂**：多时间框架（短/中/长线论据）被放在最后，与核心判研割裂。
3. **重复板块**：独立的 `ScenarioAnalysis` 与 AIVerdict 内部已有的「乐观/基准/悲观」三情景卡片（`bull_case/base_case/bear_case`）完全重复。

此外，左侧股票列表无法手动排序。

---

## 2. 目标

- 统一 AI 分析 Tab 所有板块卡片的视觉规范，消除宽度/圆角/边框观感差异。
- 按「决策逻辑」重排板块顺序。
- 删除重复的独立情景分析板块。
- 左侧股票列表支持拖拽排序并持久化。

---

## 3. 设计

### 3.1 板块样式统一（以 AIVerdict 为标准）

统一规范（取自 AIVerdict 主卡片）：

| 属性 | 标准值 |
|------|--------|
| 圆角 | `rounded-[2rem]` |
| 横向内边距 | `px-4 md:px-10` |
| 边框 | `border border-neutral-100 dark:border-zinc-800` |
| 背景 | `bg-white dark:bg-zinc-900` |

向标准对齐的组件（修改最外层容器）：
- `RiskAnalysis.tsx`（当前 `rounded-xl p-6 border-neutral-200`）
- `MultiTimeframeAnalysis.tsx`（当前 `rounded-xl p-4 border-neutral-700`）
- `KeyAssumptions.tsx`（当前无横向 px）
- `CatalystTimeline.tsx`
- `PositionOverlay.tsx`（当前 `rounded-[28px] px-5 md:px-7`）

约束：仅改最外层容器的圆角/内边距/边框/背景，不动各板块的内部布局与逻辑。

### 3.2 板块顺序（按决策逻辑）

AI 分析 Tab 新顺序（`StockDetail.tsx` 中 `resolvedActiveTab === "analysis"` 分支）：

```
1. AIVerdict        判研指标（含三情景卡片、交易执行区间、Truth Tracker）
2. PositionOverlay  持仓影响
3. MultiTimeframeAnalysis  多时间框架（短/中/长线论据）
4. KeyAssumptions   关键假设断点
5. CatalystTimeline 催化剂时间轴
6. RiskAnalysis     风险分析
```

逻辑：先给结论 → 对我持仓的影响 → 多周期论据 → 什么假设会推翻 → 什么催化剂会推动 → 风险兜底。

### 3.3 删除重复板块

- 删除 `StockDetail.tsx` 中独立的 `<ScenarioAnalysis ... />` 渲染（保留 AIVerdict 内部三情景卡片）。
- 移除 `ScenarioAnalysis` 的 import。
- `enhancedAnalysis` 数据消费中 `scenario_analysis` 不再用于渲染；如后端增强分析请求可按需跳过 scenario 以省一次 AI 调用（次要优化，不阻塞）。
- `ScenarioAnalysis.tsx` 组件文件保留（不删文件，仅停用引用），以便回滚。

### 3.4 左侧列表拖拽排序

- 依赖：`@dnd-kit/core` + `@dnd-kit/sortable`（前端新增）。
- 后端：`PATCH /api/v1/portfolio/reorder` 已存在（`ReorderPortfolioUseCase`），入参 `orders: [{ticker, sort_order}]`。
- 前端 `PortfolioList.tsx`：
  - 列表项包成 `SortableContext` + `useSortable`。
  - 拖动结束本地即时重排（乐观更新）。
  - 释放后调用 `reorder` 接口持久化，传完整新顺序的 `[{ticker, sort_order}]`。
  - 接口失败：回滚到拖动前顺序，并提示用户。
- 触控支持：dnd-kit 的 PointerSensor/TouchSensor，保证移动端可用。

---

## 4. 数据流（拖拽）

```
用户拖动列表项
  → onDragEnd 计算新顺序
  → setState 本地乐观重排（UI 立即更新）
  → PATCH /reorder 持久化
      成功 → 保持
      失败 → 回滚为拖动前顺序 + toast 提示
```

---

## 5. 不做（YAGNI）

- 不删除 `ScenarioAnalysis.tsx` 文件本体（仅停用引用，便于回滚）。
- 不重构各板块内部布局，只统一外层容器。
- 不引入通用 `SectionCard` 抽象组件（本次以 className 对齐即可，避免改动所有板块结构）。
- 不调整「标的信息」Tab 的板块。

---

## 6. 验证

- 本地起前后端（前端 3001），登录后查看 GOOGL/MU AI 分析 Tab：
  - 各板块圆角/内边距/边框一致。
  - 顺序为 3.2 所列。
  - 无独立情景板块，AIVerdict 内三情景卡片仍在。
- 左侧列表拖动一只股票到新位置，刷新页面后顺序保持（验证持久化）。
- `npm run build` / `tsc --noEmit` 通过。
