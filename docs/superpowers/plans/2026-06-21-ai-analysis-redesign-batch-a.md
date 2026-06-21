# AI 分析页重构 批次 A（删重复+砍低价值）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 AI 分析页的重复内容与低价值模块，页面更短、无重复、功能不减。

**Architecture:** 纯前端删减。逐个移除已审计认定的重复/低价值 UI 块，移除随之失效的 import 与未用 helper。批次 B/C 后续单独做。

**Tech Stack:** Next.js 16 / React / TypeScript / Tailwind

## Global Constraints

- 无前端测试框架；每个任务的门禁是 `cd frontend && npx tsc --noEmit`，最后一个任务额外跑 `npm run build`。
- 只删，不新增功能；不改后端。
- 删掉的整模块（RiskAnalysis）组件文件保留在磁盘，仅移除渲染引用，便于回滚。
- 移除某块后若其专用 helper/import 变为未使用，一并清除（避免 lint/未用告警）。
- 提交信息结尾附：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 砍掉整个风险分析模块的渲染

**Files:**
- Modify: `frontend/components/features/StockDetail.tsx`（import 行 ~34；渲染段 ~450-458）

**Interfaces:** Consumes/Produces: 无

- [ ] **Step 1: 移除 RiskAnalysis 渲染块**

删除 StockDetail.tsx 中这段（`enhancedAnalysis.data?.risk_analysis && (...)` 整块）：

```tsx
                {enhancedAnalysis.data?.risk_analysis && (
                    <RiskAnalysis
                        ticker={selectedItem?.ticker || ""}
                        riskAnalysis={enhancedAnalysis.data.risk_analysis}
                        loading={enhancedAnalysis.loading === "risk" || enhancedAnalysis.loading === "all"}
                    />
                )}
```

- [ ] **Step 2: 移除 RiskAnalysis import**

删除 StockDetail.tsx 顶部：`import { RiskAnalysis } from "./stock-detail/RiskAnalysis";`（文件保留磁盘，仅删引用）。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（RiskAnalysis 不再被引用，无未用 import 报错）

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/StockDetail.tsx
git commit -m "refactor(ai-analysis): 砍掉风险分析四卡模块（批次A，将由一句话风险提示替代）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 砍掉情绪偏差 bar

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（调用处 ~421；组件定义 `InlineSentimentBar` ~670-起）

**Interfaces:** 无

- [ ] **Step 1: 移除调用**

删除 AIVerdict.tsx 第 ~421 行的调用：
```tsx
                            <InlineSentimentBar sentimentScore={aiData.sentiment_score || 58} />
```
若其外层有专为它包裹的容器 div（仅含这一行），一并删除外层容器。

- [ ] **Step 2: 移除 InlineSentimentBar 组件定义**

删除 `function InlineSentimentBar({ sentimentScore }: ...) { ... }` 整个函数定义（从 `function InlineSentimentBar` 到其闭合 `}`，含「0: 极度看空 / 100: 极度看多」刻度尺）。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误。再 grep 确认无残留引用：`grep -n "InlineSentimentBar" frontend/components/features/stock-detail/AIVerdict.tsx` 应无输出。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "refactor(ai-analysis): 砍掉情绪偏差 bar（与信心三维重复，批次A）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 砍掉 Header 顶部价格三卡 + 执行策略横幅 + 风险回报卡

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`

**Interfaces:** 无

- [ ] **Step 1: 移除 Header 顶部三卡（止损/建仓区间/目标止盈）**

在「交易执行区间」标题（第 ~434 行）上方，有一排 止损/建仓区间/目标止盈 三卡（含第 441/451/460 行的标签）。这排卡与下方可视化轴 tick 完全重复。删除这排三卡的整个容器 div（标题行之前、与轴重复的那组价格卡），保留「交易执行区间」标题与可视化轴本身。

- [ ] **Step 2: 移除「风险回报」执行详情卡**

删除执行详情 6 卡中的「风险回报」那张（第 ~1016 行 `风险回报` 标签所在的卡片 div 整块）。Header 双 R/R 已表达此信息。

- [ ] **Step 3: 移除「执行策略」横幅**

删除第 ~1040 行 `执行策略：` 所在的横幅块整段（`action_advice` 已在折叠详情完整呈现）。

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "refactor(ai-analysis): 删重复点位三卡/风险回报卡/执行策略横幅（批次A）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: MultiTimeframe 砍 key_levels 三价位 + 置信度%

**Files:**
- Modify: `frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx`

**Interfaces:** 无

- [ ] **Step 1: 移除置信度块**

删除每行的「置信度」展示块（第 ~140 行 `置信度` 标签 + 第 ~145 行 width 进度条 + 第 ~149 行百分比文本所在的整个容器）。

- [ ] **Step 2: 移除 key_levels 三价位块**

删除渲染 `tf.data.key_levels.map(...)`（第 ~163-170 行，含「支撑/当前/阻力」三价位）的整块。保留每行的 趋势、标签、一句策略建议。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（`key_levels`/`confidence` 字段定义保留在 type 里无妨，仅不渲染）

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx
git commit -m "refactor(ai-analysis): 多时间框架砍 key_levels 与置信度%（与交易轴重复，批次A）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Truth Tracker 砍「当时价」列 + KeyAssumptions 砍提示语

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（Truth Tracker 表头/行，「当时价」第 ~1091 行）
- Modify: `frontend/components/features/stock-detail/KeyAssumptions.tsx`（提示语 第 ~105 行）

**Interfaces:** 无

- [ ] **Step 1: 移除 Truth Tracker「当时价」列**

Truth Tracker 表格当前是 `grid-cols-[auto_1fr_auto_auto_auto]`（日期/动作/当时价/至今表现/结果）。移除「当时价」列：删表头第 ~1091 行的 `<span ...>当时价</span>`，删每行对应的当时价 `<span>`（`hPrice ? "$..." : "--"` 那个），并把表头与行的 grid 列模板从 5 列改为 4 列 `grid-cols-[auto_1fr_auto_auto]`。

- [ ] **Step 2: 移除 KeyAssumptions 提示语**

删除 KeyAssumptions.tsx 第 ~105 行的空话提示：
```
点击卡片可切换查看状态，建议持续关注这一假设是否被市场数据证伪。
```
连同其包裹的 `<span>`/`<p>` 元素一并删除。

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3`
Expected: tsc 无错，`✓ Compiled successfully`

- [ ] **Step 4: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx frontend/components/features/stock-detail/KeyAssumptions.tsx
git commit -m "refactor(ai-analysis): Truth Tracker 去当时价列 + KeyAssumptions 去提示语（批次A）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 本地验证批次 A

**Files:** 无

- [ ] **Step 1: 门禁**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3`
Expected: 通过

- [ ] **Step 2: 人工核对**

本地 3001 登录看 GOOGL/MU AI 分析 Tab：
- 无风险分析四卡模块
- 无情绪偏差 bar
- 交易执行区间不再有顶部三卡重复（只剩轴）；无风险回报卡、无执行策略横幅
- 多时间框架每行无置信度%、无支撑/当前/阻力三价位（只剩趋势+策略）
- Truth Tracker 表无「当时价」列（4 列）
- KeyAssumptions 无底部提示语空话
- 页面明显变短

- [ ] **Step 3: 无额外提交**

---

## 验证清单（对照 spec 批次 A）

- 砍 Header 顶部价格三卡 → Task 3 ✅
- 砍风险回报卡 + 执行策略横幅 → Task 3 ✅
- 砍情绪偏差 bar → Task 2 ✅
- 砍整个 RiskAnalysis → Task 1 ✅
- 砍 MultiTimeframe key_levels + 置信度% → Task 4 ✅
- 砍 KeyAssumptions 提示语 → Task 5 ✅
- 砍 Truth Tracker「当时价」列 → Task 5 ✅
