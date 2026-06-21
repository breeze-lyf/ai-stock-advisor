# AI 信号历史展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把个股 AI 分析页的 Truth Tracker 从「最近 3 张卡片」升级为「完整信号历史紧凑时间线」，并修正胜负判定覆盖买/卖/持有/观望四种动作。

**Architecture:** 纯前端单组件改造。把 `AIVerdict.tsx` 内的 `TruthTracker` 重写为竖向时间线列表，展示全部 `analysisHistory`；胜负判定逻辑抽成同文件内的纯函数 `getSignalOutcome`，便于正确性核对。

**Tech Stack:** Next.js 16 / React / TypeScript / Tailwind / date-fns（已用）

## Global Constraints

- 无前端测试框架；验证门禁为 `cd frontend && npx tsc --noEmit` 与 `npm run build`，外加本地人工核对。
- 深色模式用 neutral/zinc，不用 slate。
- 盈亏口径不变：`pl = history_price ? (current_price - history_price)/history_price*100 : null`。不拉历史 K 线。
- 风格遵循页面现有规范（中性灰、紧凑），不引入新风格。
- 提交信息结尾附：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: 抽出胜负判定纯函数 getSignalOutcome

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（在 `TruthTracker` 定义之前加一个纯函数）

**Interfaces:**
- Produces: `getSignalOutcome(immediateAction: string | null | undefined, pl: number | null): "win" | "loss" | null`
  - `pl === null` → 返回 `null`（无表现数据，不判定）
  - action 含「买」或「持有」→ `pl > 0 ? "win" : "loss"`
  - action 含「卖」或「减」→ `pl < 0 ? "win" : "loss"`
  - action 含「观望」或其他/空 → `null`（无建议动作，不判定）

- [ ] **Step 1: 在 TruthTracker 函数定义上方新增纯函数**

在 `AIVerdict.tsx` 中 `function TruthTracker({` 那一行的正上方插入：

```tsx
// 信号胜负判定：覆盖买/卖/持有/观望四种动作。
// pl 为 null（无 history_price）时不判定；观望/未知动作不判定。
function getSignalOutcome(
    immediateAction: string | null | undefined,
    pl: number | null,
): "win" | "loss" | null {
    if (pl === null) return null;
    const a = immediateAction || "";
    if (a.includes("买") || a.includes("持有")) return pl > 0 ? "win" : "loss";
    if (a.includes("卖") || a.includes("减")) return pl < 0 ? "win" : "loss";
    return null; // 观望及其他：无建议动作，不计胜负
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误（新增的是独立纯函数，暂未被调用——若 lint 报未使用，下一 Task 即接入；tsc 对未使用函数不报错）

- [ ] **Step 3: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "feat(truth-tracker): 抽出 getSignalOutcome 胜负判定纯函数，覆盖四动作

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: TruthTracker 改为完整信号历史时间线

**Files:**
- Modify: `frontend/components/features/stock-detail/AIVerdict.tsx`（`TruthTracker` 组件 body，约 1062-1132 行）

**Interfaces:**
- Consumes: `getSignalOutcome`（Task 1）；`analysisHistory`、`selectedItem.current_price`（现有 props）；`format` / `zhCN`（date-fns，文件已 import）；`clsx`（已 import）；`Clock`（已 import）。

- [ ] **Step 1: 替换 TruthTracker 的 return 内容为时间线列表**

将 `TruthTracker` 函数体内 `return (...)` 整段（外层卡片容器内的标题 + 卡片网格）替换为：标题保留，网格改为竖向时间线。完整新 return：

```tsx
    return (
        <div className="rounded-[28px] border border-neutral-100 bg-white px-5 py-4.5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 md:px-7">
            <div className="mb-4 flex items-center gap-3">
                <Clock className="h-5 w-5 text-blue-600" />
                <h3 className="text-sm font-black text-neutral-900 dark:text-white uppercase tracking-wider">AI 信号追踪与复盘 (The Truth Tracker)</h3>
                <span className="ml-auto text-[10px] font-bold text-neutral-400">{analysisHistory.length} 条信号</span>
            </div>

            {analysisHistory.length === 0 ? (
                <div className="py-8 text-center text-[11px] text-neutral-400">暂无历史信号，运行 AI 分析后将在此累积</div>
            ) : (
                <div className="max-h-[420px] overflow-y-auto custom-scrollbar -mx-1 px-1">
                    {/* 表头 */}
                    <div className="grid grid-cols-[auto_1fr_auto_auto_auto] items-center gap-3 border-b border-neutral-100 pb-2 dark:border-zinc-800 text-[8px] font-bold uppercase tracking-wider text-neutral-400">
                        <span>日期</span>
                        <span>动作</span>
                        <span className="text-right">当时价</span>
                        <span className="text-right">至今表现</span>
                        <span className="text-right pr-1">结果</span>
                    </div>
                    {analysisHistory.map((report, idx) => {
                        const hPrice = report.history_price;
                        const cPrice = selectedItem.current_price;
                        const pl = hPrice ? ((cPrice - hPrice) / hPrice) * 100 : null;
                        const outcome = getSignalOutcome(report.immediate_action, pl);
                        const action = report.immediate_action || "--";
                        return (
                            <div
                                key={idx}
                                className="grid grid-cols-[auto_1fr_auto_auto_auto] items-center gap-3 border-b border-neutral-50 py-2.5 last:border-0 dark:border-zinc-800/50"
                            >
                                <span className="text-[10px] font-bold tabular-nums text-neutral-400 whitespace-nowrap" suppressHydrationWarning>
                                    {report.created_at ? format(new Date(report.created_at + (report.created_at.includes('Z') ? '' : 'Z')), "yy/MM/dd", { locale: zhCN }) : "--"}
                                </span>
                                <span className={clsx(
                                    "truncate text-[11px] font-black",
                                    action.includes("买") || action.includes("持有") ? "text-emerald-600" :
                                        action.includes("卖") || action.includes("减") ? "text-rose-600" : "text-neutral-500"
                                )}>
                                    {action}
                                </span>
                                <span className="text-right text-[11px] font-black tabular-nums text-neutral-600 dark:text-neutral-300 whitespace-nowrap">
                                    {hPrice ? `$${hPrice.toFixed(2)}` : "--"}
                                </span>
                                <span className={clsx(
                                    "text-right text-[11px] font-black tabular-nums whitespace-nowrap",
                                    pl === null ? "text-neutral-400" : pl >= 0 ? "text-emerald-600" : "text-rose-600"
                                )}>
                                    {pl !== null ? `${pl >= 0 ? "+" : ""}${pl.toFixed(2)}%` : "--"}
                                </span>
                                <span className="text-right pr-1">
                                    {outcome === null ? (
                                        <span className="text-[9px] font-bold text-neutral-300 dark:text-neutral-600">--</span>
                                    ) : (
                                        <span className={clsx(
                                            "rounded px-1.5 py-0.5 text-[8px] font-black uppercase",
                                            outcome === "win" ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"
                                        )}>
                                            {outcome === "win" ? "命中" : "回撤"}
                                        </span>
                                    )}
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
```

注意：去掉了 `.slice(0, 3)` → 展示全部；外层卡片边框 `border-neutral-200` → `border-neutral-100` 与页面标准一致。

- [ ] **Step 2: 确认 risk_level/confidence_level 不再被引用不报错**

新结构不再展示 risk/confidence 标签（信息密度优先）。确认无残留引用导致 unused 警告即可——它们来自 `report` 对象的可选字段，不引用不报错。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: 构建**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: `✓ Compiled successfully`

- [ ] **Step 5: Commit**

```bash
git add frontend/components/features/stock-detail/AIVerdict.tsx
git commit -m "feat(truth-tracker): 升级为完整信号历史时间线，展示全部信号

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 本地验证

**Files:** 无（验证）

- [ ] **Step 1: 门禁**

Run: `cd frontend && npx tsc --noEmit && npm run build 2>&1 | tail -3`
Expected: tsc 无错，构建成功

- [ ] **Step 2: 人工核对**

本地前端（3001）登录后打开 MU 或 GOOGL（DB 中有十余条历史）的 AI 分析 Tab，核对：
- Truth Tracker 标题右侧显示「N 条信号」，列表显示全部历史（不止 3 条），超高可滚动
- 每行：日期 / 动作（着色）/ 当时价 / 至今表现 / 命中-回撤
- 买入/持有看涨命中、卖出看跌命中判定正确；观望显示 `--`；无 history_price 行表现与结果均 `--`
- 空历史股票显示「暂无历史信号」占位

- [ ] **Step 3: 无额外提交**

---

## 验证清单（对照 spec）

- spec 3.1 时间线展示 + 去 slice → Task 2 ✅
- spec 3.2 四动作判定 + 现价回算口径 → Task 1（逻辑）+ Task 2（接入）✅
- spec 6 验证 → Task 3 ✅
