# 个股详情页 UI 重构 + 列表拖拽排序 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一个股详情页「AI 分析」Tab 各板块卡片样式、重排顺序、删除重复情景板块，并为左侧股票列表加拖拽排序。

**Architecture:** 纯前端改动（拖拽后端 API 已存在）。板块样式以 className 对齐到 AIVerdict 标准；顺序在 `StockDetail.tsx` 调整；拖拽用 @dnd-kit 在 `PortfolioList.tsx` 实现，乐观更新 + 失败回滚，复用现有 `reorderPortfolio` helper。

**Tech Stack:** Next.js 16 / React / TypeScript / Tailwind / @dnd-kit

## Global Constraints

- 深色模式用中性灰（neutral/zinc），不引入蓝色相（slate）。
- 卡片统一标准：`rounded-[2rem]`、横向内边距 `px-4 md:px-10`、`border border-neutral-100 dark:border-zinc-800`、`bg-white dark:bg-zinc-900`。
- 仅改各板块最外层容器，不动内部布局逻辑。
- 验证命令在 `frontend/` 目录下运行：`npx tsc --noEmit`。
- 提交信息结尾附：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 统一 RiskAnalysis 与 MultiTimeframeAnalysis 容器样式

**Files:**
- Modify: `frontend/components/features/stock-detail/RiskAnalysis.tsx`（根容器 line ~88）
- Modify: `frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx`（根容器 line ~100）

**Interfaces:**
- Consumes: 无
- Produces: 无（纯样式）

- [ ] **Step 1: 改 RiskAnalysis 根容器**

把 RiskAnalysis.tsx 中非 loading 状态的根容器（当前 `bg-white dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700`）改为标准：

```tsx
<div className="bg-white dark:bg-zinc-900 rounded-[2rem] px-4 md:px-10 py-6 border border-neutral-100 dark:border-zinc-800">
```

- [ ] **Step 2: 改 MultiTimeframeAnalysis 根容器**

MultiTimeframeAnalysis.tsx 当前根是 `<div className="space-y-4">`（无卡片外壳）。包一层标准卡片容器：

```tsx
<div className="bg-white dark:bg-zinc-900 rounded-[2rem] px-4 md:px-10 py-6 border border-neutral-100 dark:border-zinc-800">
  <div className="space-y-4">
    {/* 原有内容 */}
  </div>
</div>
```

注意：内部各 timeframe 卡片（line ~117 的 `rounded-xl ... border-neutral-200 dark:border-neutral-700`）保持不动（那是嵌套子卡，不在统一范围）。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/stock-detail/RiskAnalysis.tsx frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx
git commit -m "style(stock-detail): RiskAnalysis/MultiTimeframe 容器对齐 AIVerdict 标准

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 统一 KeyAssumptions / CatalystTimeline / PositionOverlay 容器样式

**Files:**
- Modify: `frontend/components/features/stock-detail/KeyAssumptions.tsx`（根容器 line ~1）
- Modify: `frontend/components/features/stock-detail/CatalystTimeline.tsx`（根容器 line ~1）
- Modify: `frontend/components/features/stock-detail/PositionOverlay.tsx`（根容器 line ~1）

**Interfaces:**
- Consumes: 无
- Produces: 无（纯样式）

- [ ] **Step 1: 改 KeyAssumptions 根容器**

当前：`bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-2xl overflow-hidden`
改为：

```tsx
<div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] px-4 md:px-10 py-6 overflow-hidden">
```

- [ ] **Step 2: 改 CatalystTimeline 根容器**

当前：`bg-white dark:bg-zinc-900 border border-neutral-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden`
改为：

```tsx
<div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] px-4 md:px-10 py-6 shadow-sm overflow-hidden">
```

- [ ] **Step 3: 改 PositionOverlay 根容器**

当前：`rounded-[28px] border border-neutral-200 bg-white px-5 py-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 md:px-7`
改为：

```tsx
<div className="rounded-[2rem] border border-neutral-100 bg-white px-4 py-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 md:px-10">
```

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 5: Commit**

```bash
git add frontend/components/features/stock-detail/KeyAssumptions.tsx frontend/components/features/stock-detail/CatalystTimeline.tsx frontend/components/features/stock-detail/PositionOverlay.tsx
git commit -m "style(stock-detail): KeyAssumptions/Catalyst/Position 容器对齐标准

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 删除重复情景板块 + 重排 AI 分析 Tab 顺序

**Files:**
- Modify: `frontend/components/features/StockDetail.tsx`（line ~422-472 的 analysis 分支；import 区）

**Interfaces:**
- Consumes: 现有 AIVerdict / PositionOverlay / MultiTimeframeAnalysis / KeyAssumptions / CatalystTimeline / RiskAnalysis 组件
- Produces: 无

- [ ] **Step 1: 移除 ScenarioAnalysis import**

删除 StockDetail.tsx 顶部的 `import { ScenarioAnalysis } from "./stock-detail/ScenarioAnalysis";`（保留组件文件本身不删）。

- [ ] **Step 2: 重排 analysis 分支并删除 ScenarioAnalysis 渲染**

把 `resolvedActiveTab === "analysis"` 分支内的板块改为以下顺序，并删除 `<ScenarioAnalysis .../>` 块（即原 enhancedAnalysis.data.scenario_analysis 渲染段）：

```tsx
{resolvedActiveTab === "analysis" && (
  <>
    <AIVerdict
        selectedItem={selectedItem}
        aiData={aiData}
        analysisHistory={analysisHistory as AnalysisHistoryItem[]}
        analyzing={analyzing}
        onAnalyze={onAnalyze}
        currency={currency}
        sanitizePrice={sanitizePrice}
    />

    <PositionOverlay
        selectedItem={selectedItem}
        aiData={aiData}
        currency={currency}
        sanitizePrice={sanitizePrice}
        positionImpact={positionImpact}
    />

    {enhancedAnalysis.data?.multi_timeframe && (
        <MultiTimeframeAnalysis
            ticker={selectedItem?.ticker || ""}
            analysis={enhancedAnalysis.data.multi_timeframe}
            loading={enhancedAnalysis.loading === "timeframe" || enhancedAnalysis.loading === "all"}
        />
    )}

    <KeyAssumptions assumptions={aiData?.key_assumptions} />

    <CatalystTimeline catalysts={aiData?.catalysts} />

    {enhancedAnalysis.data?.risk_analysis && (
        <RiskAnalysis
            ticker={selectedItem?.ticker || ""}
            riskAnalysis={enhancedAnalysis.data.risk_analysis}
            loading={enhancedAnalysis.loading === "risk" || enhancedAnalysis.loading === "all"}
        />
    )}
  </>
)}
```

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误（ScenarioAnalysis 不再被引用，无未使用报错——已删 import）

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/StockDetail.tsx
git commit -m "refactor(stock-detail): 删重复情景板块 + 按决策逻辑重排 AI 分析顺序

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 安装 @dnd-kit 依赖

**Files:**
- Modify: `frontend/package.json`、`frontend/package-lock.json`

**Interfaces:**
- Consumes: 无
- Produces: `@dnd-kit/core`、`@dnd-kit/sortable`、`@dnd-kit/utilities` 三个包可被 import

- [ ] **Step 1: 安装**

```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

- [ ] **Step 2: 验证安装**

Run: `ls frontend/node_modules/@dnd-kit`
Expected: 出现 `core`、`sortable`、`utilities` 三个目录

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(deps): 添加 @dnd-kit 用于列表拖拽排序

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: PortfolioList 拖拽排序

**Files:**
- Modify: `frontend/components/features/PortfolioList.tsx`

**Interfaces:**
- Consumes: `reorderPortfolio(orders: { ticker: string; sort_order: number }[])`（已存在于 `frontend/features/portfolio/api.ts:44`）；现有 props `portfolio`、`onRefresh`、`selectedTicker`、`onSelectTicker`、`sortBy` 状态。
- Produces: 无

- [ ] **Step 1: 引入 dnd-kit imports**

在 PortfolioList.tsx 顶部加：

```tsx
import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
```

- [ ] **Step 2: 抽出 SortableRow 包装组件**

在 PortfolioList 函数外（同文件顶层）新增一个轻量包装，仅在 `sortBy === "manual"` 时启用拖拽。它包住原列表项 JSX。新增组件：

```tsx
function SortableRow({ id, disabled, children }: { id: string; disabled: boolean; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id, disabled });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    cursor: disabled ? undefined : "grab",
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </div>
  );
}
```

- [ ] **Step 3: 加 sensors 与拖拽结束处理**

在 PortfolioList 组件体内（现有 useState 附近）加：

```tsx
const sensors = useSensors(
  useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 8 } })
);
const dragEnabled = sortBy === "manual" && !onlyHoldings;

const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  if (!over || active.id === over.id) return;
  const oldIndex = sortedPortfolio.findIndex(p => p.ticker === active.id);
  const newIndex = sortedPortfolio.findIndex(p => p.ticker === over.id);
  if (oldIndex < 0 || newIndex < 0) return;
  const reordered = arrayMove(sortedPortfolio, oldIndex, newIndex);
  const orders = reordered.map((p, idx) => ({ ticker: p.ticker, sort_order: idx }));
  try {
    await reorderPortfolio(orders);
    onRefresh();
  } catch {
    alert("排序更新失败");
    onRefresh();
  }
};
```

注意：`dragEnabled` 仅在手动排序且非仅持仓过滤时启用，避免与列排序/过滤冲突。

- [ ] **Step 4: 用 DndContext + SortableContext 包裹列表**

把 `sortedPortfolio.map(...)` 外层包裹（line ~244）。将原来直接 `.map` 渲染的每个 `<div key={item.ticker}>` 行用 `<SortableRow id={item.ticker} disabled={!dragEnabled}>` 包住。列表外层：

```tsx
<DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
  <SortableContext items={sortedPortfolio.map(p => p.ticker)} strategy={verticalListSortingStrategy}>
    {sortedPortfolio.map((item) => (
      <SortableRow key={item.ticker} id={item.ticker} disabled={!dragEnabled}>
        {/* 原有的行 div 内容保持不变 */}
      </SortableRow>
    ))}
  </SortableContext>
</DndContext>
```

注意：原行内的 `onClick={() => onSelectTicker(item.ticker)}` 保留——PointerSensor 的 `distance: 5` 约束保证「点击」与「拖动」可区分（移动 <5px 视为点击）。

- [ ] **Step 5: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/components/features/PortfolioList.tsx
git commit -m "feat(portfolio): 左侧列表拖拽排序（手动排序模式下，乐观更新+失败回滚）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 本地验证全部改动

**Files:** 无（验证）

**Interfaces:**
- Consumes: 全部前序改动
- Produces: 无

- [ ] **Step 1: 构建检查**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -20`
Expected: 构建成功，无类型错误

- [ ] **Step 2: 本地起服务并人工核对**

本地前端跑在 3001（参考之前 start.sh dev）。登录后打开任一个股 AI 分析 Tab，核对：
- 各板块圆角/内边距/边框一致（无明显宽窄差异）
- 顺序为：判研 → 持仓 → 多时间框架 → 关键假设 → 催化剂 → 风险
- 无独立情景板块，AIVerdict 内三情景卡片仍在
- 左侧列表「手动排序」模式下可拖动，释放后刷新顺序保持；切到列排序时不可拖

- [ ] **Step 3: 无额外提交**（验证任务，前序已各自提交）

---

## 验证清单（对照 spec）

- spec 3.1 样式统一 → Task 1、2 ✅
- spec 3.2 顺序调整 → Task 3 ✅
- spec 3.3 删除重复板块 → Task 3 ✅
- spec 3.4 拖拽排序 → Task 4、5 ✅
- spec 6 验证 → Task 6 ✅
