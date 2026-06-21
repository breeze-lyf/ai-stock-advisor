# AI 分析页重构 批次 B（排版统一）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一 AI 分析页排版：标识符在卡外、拆分过长的判研模块为两个独立卡片、详细诊断去套娃。

**Architecture:** 纯前端排版重构。标识符标准 = 卡外「竖色条+标题」+ 下方白底卡片内容。把 AIVerdictContent 的内部 6 块按「判研与交易计划 / 深度论据」拆成两个各带卡外标题的独立卡片；去掉详细诊断的双层边框。

**Tech Stack:** Next.js 16 / React / TypeScript / Tailwind

## Global Constraints

- 无前端测试框架；门禁 `cd frontend && npx tsc --noEmit`，末任务加 `npm run build`。
- 标识符标准：模块 = 卡外「竖色条(`h-8 w-1.5 rounded-full` + 发光) + `h2 text-xl font-black uppercase`」(顶格) + 下方白底卡片(`rounded-[2rem] px-4 md:px-10 py-6 border border-neutral-100 dark:border-zinc-800 bg-white dark:bg-zinc-900`)。参考 MarketAnalysis.tsx 的标题栏写法。
- 深色模式用 neutral/zinc，不用 slate。
- 只改排版结构，不改数据/逻辑/字段。
- 提交信息结尾附：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 详细诊断去套娃

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（块6，~523-546 行）

**Interfaces:** 无

- [ ] **Step 1: 去掉展开面板的内层边框**

块6「详细诊断研判逻辑」是：一个带边框的折叠按钮 + 展开后一个带边框的内层面板(~540 行 `mt-3 rounded-[22px] border ... bg-white`)，整体又嵌在 AIVerdictContent 的外层卡片里 → 套娃。

把展开面板(540 行那个 div)的边框与独立背景去掉，让它直接承接按钮、不再形成第二层框。将 540 行的：
```tsx
                    <div className="mt-3 rounded-[22px] border border-neutral-200 bg-white px-5 py-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300 dark:border-zinc-800 dark:bg-zinc-950">
```
改为（去边框、去独立底色，仅留间距）：
```tsx
                    <div className="mt-3 px-1 py-2 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "style(ai-analysis): 详细诊断展开面板去内层边框，消除套娃（批次B）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 多时间框架标识符统一确认

**Files:**
- Modify (若需): `frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx`

**Interfaces:** 无

- [ ] **Step 1: 核对当前标题栏是否已符合标准**

MultiTimeframeAnalysis 当前根是 `<div className="...rounded-[2rem] px-4 md:px-10 py-6 border...">`，标题在卡片**内部**（竖条+h2 在卡内顶部）。标准要求标题栏在卡片**外**。

把结构改为：最外层 `<div className="space-y-3">`，内含 (1) 卡外标题栏 `<div className="flex items-center gap-3"><div className="h-8 w-1.5 bg-blue-600 rounded-full shadow-[0_0_12px_rgba(37,99,235,0.5)]"/><h2 className="text-xl font-black tracking-tight text-neutral-900 dark:text-neutral-100 uppercase">多时间框架分析</h2></div>` (2) 下方卡片 `<div className="bg-white dark:bg-zinc-900 rounded-[2rem] px-4 md:px-10 py-6 border border-neutral-100 dark:border-zinc-800">` 包住原 timeframes 列表内容。即：把原本在卡内的标题提到卡外，卡片只留内容。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/components/features/stock-detail/MultiTimeframeAnalysis.tsx
git commit -m "style(ai-analysis): 多时间框架标题栏提到卡片外，对齐标识符标准（批次B）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 拆分 AIVerdictContent — 模块1「判研与交易计划」

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（AIVerdictContent return，~288-549 行）

**Interfaces:**
- Produces: AIVerdictContent 的 return 改为「外层 `<div className="space-y-8">` 包两个区块」。本任务先建模块1卡片，模块2(块5/6)暂时原样保留在第二张临时卡里（Task 4 再正式化）。

- [ ] **Step 1: 把单一大卡拆成两张卡的骨架**

当前 AIVerdictContent return 是一个大 div（289 行 `space-y-0 ... rounded-3xl ... border`）顺序包含块1-6。改为：

```tsx
    return (
        <div className="space-y-8">
            {/* 模块1：AI 判研与交易计划 */}
            <div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] overflow-hidden">
                {/* 块1 Header & Sentiment / 块2 Trade Axis / 块3 Core Summary / 块4 Decision Brief 原样放这里 */}
            </div>

            {/* 模块2：深度论据（含块5 情景、块6 详细诊断）*/}
            <div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] overflow-hidden">
                {/* 块5 Scenario Panel / 块6 Logical Breakdown 原样放这里 */}
            </div>
        </div>
    );
```

具体操作：把原块1-4（注释 `{/* 1. */}` 到 `{/* 4. */}`，约 291-521 行）整体移入第一张卡 div；把原块5-6（`{/* 5. */}`、`{/* 6. */}`）整体移入第二张卡 div。删除原最外层 `rounded-3xl shadow-xl` 大 div（被两张新卡替代）。不改各块内部内容。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（JSX 平衡，块内容不变）

- [ ] **Step 3: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "refactor(ai-analysis): AIVerdictContent 拆为判研计划/深度论据两张卡（批次B）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 给两个模块加卡外竖条标题

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`

**Interfaces:**
- Consumes: Task 3 的两张卡结构。

- [ ] **Step 1: 模块1/模块2 各加卡外标题栏**

AIVerdict 顶层 return（~38-67 行）当前有一个总标题「AI 智能判研指标」+ 深度诊断按钮，再渲染 `<AIVerdictContent .../>`。现在 AIVerdictContent 产出两张卡，需各自有卡外标题。

调整：把 AIVerdict 顶层的总标题「AI 智能判研指标」改名为模块1标题「AI 判研与交易计划」并保留深度诊断按钮在其右侧；该标题栏作为模块1的卡外标题（放在 AIVerdictContent 第一张卡的上方）。在 AIVerdictContent 第二张卡（深度论据）上方，新增卡外标题栏：
```tsx
<div className="flex items-center gap-3 mb-4">
    <div className="h-8 w-1.5 bg-violet-600 rounded-full shadow-[0_0_12px_rgba(124,58,237,0.5)]" />
    <h2 className="text-xl font-black tracking-tight text-neutral-900 dark:text-neutral-100 uppercase">深度论据</h2>
</div>
```
实现方式：在 AIVerdictContent 的两张卡之间，第二张卡 div 之前插入上面这段标题栏；第一张卡沿用 AIVerdict 顶层已有的标题栏（确保它在第一张卡上方、卡外）。保证两个标题都是「卡外竖条+h2」结构、顶格。

- [ ] **Step 2: 类型检查 + 构建**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3`
Expected: tsc 无错，`✓ Compiled successfully`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "style(ai-analysis): 判研计划/深度论据各加卡外竖条标题（批次B）

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 本地验证批次 B

**Files:** 无

- [ ] **Step 1: 门禁**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3`
Expected: 通过

- [ ] **Step 2: 人工核对**

本地 3001 登录看 GOOGL/MU AI 分析 Tab：
- 「AI 智能判研指标」已拆成两张独立卡片：模块1「AI 判研与交易计划」(含结论/交易轴/核心摘要/决策简报)、模块2「深度论据」(含情景/详细诊断)，各有卡外竖条标题，中间有明显间隔。
- 多时间框架的标题栏在卡片外（竖条+标题在白卡上方）。
- 详细诊断展开后不再是框里套框（内层面板无独立边框）。
- 全页所有模块的标识符都在卡外、风格统一。

- [ ] **Step 3: 无额外提交**

---

## 验证清单（对照 spec 批次 B）

- 标识符统一到卡外（多时间框架 + 拆出的两模块） → Task 2, Task 4 ✅
- 拆分 AIVerdict 为两个带独立标题栏的模块 → Task 3, Task 4 ✅
- 详细诊断去套娃 → Task 1 ✅
