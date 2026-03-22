/**
 * AI 智能判研指标板块 (AI Verdict Section)
 * 职责：展示 AI 分析的完整研判结果
 * 包含子模块：
 *   - 建议操作 + 情绪偏差 (Header & Sentiment)
 *   - 交易执行轴 (Trade Axis) — 核心算法
 *   - 诊断研判逻辑 (Logic Breakdown)
 *   - 信号追踪与复盘 (Truth Tracker)
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import {
    TrendingUp, Target, Activity,
    BarChart3, Zap, AlertCircle,
    Clock, ShieldCheck, ChevronDown, ChevronUp,
    LayoutDashboard
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { zhCN } from "date-fns/locale";
import { AIVerdictProps } from "./types";
import { MarkdownWithRefs } from "./shared";
import { createSimulatedTrade } from "@/features/paper-trading/api";
import { Play } from "lucide-react";

export const AIVerdict = React.memo(function AIVerdict({
    selectedItem,
    aiData,
    analysisHistory,
    analyzing,
    onAnalyze,
    currency,
    sanitizePrice
}: AIVerdictProps) {
    return (
        <div className="space-y-6">
            {/* 标题栏：顶格对齐 */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-blue-600 rounded-full shadow-[0_0_12px_rgba(37,99,235,0.5)]" />
                    <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">AI 智能判研指标</h2>
                </div>
                <div className="flex flex-col items-center">
                    <Button
                        onClick={() => onAnalyze(true)}
                        disabled={analyzing}
                        className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-black px-6 h-10 rounded-xl hover:scale-105 transition-transform active:scale-95 mr-4 md:mr-10"
                    >
                        {analyzing ? "诊断中..." : "开启深度诊断"}
                    </Button>
                    {analyzing && (
                        <span className="text-[9px] font-bold text-blue-600 animate-pulse mt-1 mr-4 md:mr-10">
                            深度思考约需 2-3 分钟，请稍后
                        </span>
                    )}
                </div>
            </div>

            {/* 内容区：缩进 */}
            <div className="px-4 md:px-10">
                {aiData ? (
                    <AIVerdictContent
                        selectedItem={selectedItem}
                        aiData={aiData}
                        analysisHistory={analysisHistory}
                        currency={currency}
                        sanitizePrice={sanitizePrice}
                    />
                ) : (
                    <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-[2rem] text-slate-400 gap-4">
                        <BarChart3 className="h-10 w-10 opacity-10" />
                        <p className="text-[10px] font-bold uppercase tracking-[0.3em]">等待诊断报告生成...</p>
                    </div>
                )}

                {/* AI 历史信号复盘 (Signal Tracker) */}
                {analysisHistory.length > 0 && (
                    <div className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-1000">
                        <TruthTracker
                            analysisHistory={analysisHistory}
                            selectedItem={selectedItem}
                        />
                    </div>
                )}
            </div>
        </div>
    );
});

function splitHeroTitle(immediateAction?: string, triggerCondition?: string) {
    const raw = (immediateAction || "观望").trim();
    const parts = raw
        .split(/[，,；;。]/)
        .map((part) => part.trim())
        .filter(Boolean);

    const title = parts[0] || raw;
    const subtitle = parts.slice(1).join("，") || triggerCondition || "";

    return { title, subtitle };
}

function compactSentence(value?: string, maxLength = 38) {
    if (!value) return "";
    const normalized = value.replace(/\s+/g, " ").trim();
    if (normalized.length <= maxLength) return normalized;
    return `${normalized.slice(0, maxLength).trim()}...`;
}

function normalizeComparisonText(value?: string) {
    if (!value) return "";
    return value
        .replace(/^当前(?:先观察|不直接执行)[:：]\s*/u, "")
        .replace(/\s+/g, "")
        .trim()
        .toLowerCase();
}

function splitScenario(value?: string) {
    if (!value) {
        return { trigger: "", action: "" };
    }

    const triggerMatch = value.match(/(?:触发条件[:：]\s*)([^。；;]+)/);
    const actionMatch = value.match(/(?:操作[:：]\s*)([^。；;]+)/);
    if (triggerMatch || actionMatch) {
        return {
            trigger: triggerMatch?.[1]?.trim() || "",
            action: actionMatch?.[1]?.trim() || "",
        };
    }

    const parts = value
        .split(/[。；;]/)
        .map((part) => part.trim())
        .filter(Boolean);
    return {
        trigger: parts[0] || "",
        action: parts[1] || "",
    };
}

// ========================================
// AI 判研内容主体（含交易轴、情绪偏差、研判逻辑）
// ========================================

function AIVerdictContent({
    selectedItem,
    aiData,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    analysisHistory: _analysisHistory,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    currency: _currency,
    sanitizePrice
}: {
    selectedItem: AIVerdictProps["selectedItem"];
    aiData: NonNullable<AIVerdictProps["aiData"]>;
    analysisHistory: AIVerdictProps["analysisHistory"];
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
}) {
    /**
     * 加入模拟交易逻辑
     */
    const [isCreatingTrade, setIsCreatingTrade] = React.useState(false);
    const [tradeCreated, setTradeCreated] = React.useState(false);

    const handleJoinPaperTrade = async () => {
        if (!selectedItem || !aiData) return;
        setIsCreatingTrade(true);
        try {
            await createSimulatedTrade({
                ticker: selectedItem.ticker,
                entry_price: selectedItem.current_price,
                entry_reason: aiData.action_advice || "AI 推荐",
                target_price: aiData.target_price,
                stop_loss_price: aiData.stop_loss_price
            });
            setTradeCreated(true);
            setTimeout(() => setTradeCreated(false), 3000); // 3秒后恢复
        } catch (error) {
            console.error("Failed to create simulated trade:", error);
            // 可以在此加入更完善的错误提示
        } finally {
            setIsCreatingTrade(false);
        }
    };

    /**
     * 交易轴算法逻辑 (Trade Axis Algorithm)
     * 职责：将 AI 提供的 止损/建仓/目标价 映射到一个线性坐标轴上
     */
    const [isExpanded, setIsExpanded] = React.useState(false);
    
    const stop = aiData.stop_loss_price || 0;
    const target = aiData.target_price || 0;
    const current = selectedItem.current_price;
    const entryLow = aiData.entry_price_low || stop;
    const entryHigh = aiData.entry_price_high || entryLow;

    const strategyRange = target - stop;
    const buffer = strategyRange * 0.2;

    let axisMin = stop - buffer;
    let axisMax = target + buffer;

    if (current < axisMin) axisMin = current - buffer;
    if (current > axisMax) axisMax = current + buffer;

    const totalRange = axisMax - axisMin;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const _getPos = (val: number) => ((val - axisMin) / totalRange) * 100;

    const zones = [
        { name: (selectedItem?.quantity || 0) > 0 ? "止损" : "预设止损", start: axisMin, end: stop, color: "bg-rose-600", darkColor: "bg-rose-600/80", textColor: "text-rose-600 dark:text-rose-400", bgColor: "bg-rose-50 dark:bg-rose-600/10", borderColor: "border-rose-200 dark:border-rose-600/20" },
        { name: "建仓", start: stop, end: entryHigh, color: "bg-emerald-600", darkColor: "bg-emerald-600/80", textColor: "text-emerald-600 dark:text-emerald-400", bgColor: "bg-emerald-50 dark:bg-emerald-600/10", borderColor: "border-emerald-200 dark:border-emerald-600/20" },
        { name: "观望/持有", start: entryHigh, end: target, color: "bg-[#E8EAED] dark:bg-slate-600", darkColor: "bg-slate-600", textColor: "text-slate-500 dark:text-slate-400", bgColor: "bg-slate-50 dark:bg-slate-800/50", borderColor: "border-slate-200 dark:border-slate-700" },
        { name: "止盈", start: target, end: axisMax, color: "bg-blue-600", darkColor: "bg-blue-600/80", textColor: "text-blue-600 dark:text-blue-400", bgColor: "bg-blue-50 dark:bg-blue-600/10", borderColor: "border-blue-200 dark:border-blue-600/20" }
    ];

    const activeZone = zones.find(z => current >= z.start && current <= z.end) ||
        (current < axisMin ? zones[0] : zones[zones.length - 1]);

    const effectiveRR = aiData.rr_ratio;
    const { title: heroTitle, subtitle: heroSubtitle } = splitHeroTitle(aiData.immediate_action, aiData.trigger_condition);
    const actionReason = aiData.trade_setup_status === "接近触发"
        ? `当前不直接执行：${compactSentence(aiData.trigger_condition || aiData.core_logic_summary, 42)}`
        : aiData.trade_setup_status === "未触发"
            ? `当前先观察：${compactSentence(aiData.trigger_condition || aiData.core_logic_summary, 42)}`
            : "";
    const shouldShowActionReason = Boolean(actionReason) && (
        normalizeComparisonText(actionReason) !== normalizeComparisonText(heroSubtitle)
    );

    return (
        <div className="space-y-0 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-3xl overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none animate-in fade-in slide-in-from-bottom-2 duration-700">

            {/* 1. Header & Sentiment Grid */}
            <div className="py-4 px-6 md:py-6 md:px-8 bg-slate-50/50 dark:bg-white/5 border-b border-slate-100 dark:border-white/5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
                    {/* Left: Suggested Action */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <h3 className={clsx(
                                "text-3xl font-black uppercase tracking-tight",
                                aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多") ? "text-slate-900 dark:text-white" :
                                    aiData.immediate_action?.includes("卖") || aiData.immediate_action?.includes("减") ? "text-rose-600 dark:text-rose-400" :
                                        "text-slate-900 dark:text-white"
                            )}>
                                {heroTitle}
                            </h3>
                            <span className={clsx(
                                "text-[9px] font-black px-2 py-0.5 rounded-md border uppercase whitespace-nowrap",
                                activeZone.bgColor,
                                activeZone.textColor,
                                activeZone.borderColor
                            )}>
                                {activeZone.name}
                            </span>
                            <div className={clsx(
                                "flex items-center gap-1.5 px-2 py-0.5 rounded-md border ml-1",
                                parseFloat(effectiveRR || "0") >= 2.5 ? "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-600/10 dark:text-emerald-400 dark:border-emerald-600/20" :
                                    parseFloat(effectiveRR || "0") >= 1.8 ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20" :
                                        "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-600/10 dark:text-rose-400 dark:border-rose-600/20"
                            )}>
                                <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70">盈亏比 R/R</span>
                                <span className="text-[10px] font-black tabular-nums">{effectiveRR || "--"}</span>
                            </div>
                            {aiData.dominant_driver && (
                                <span className="text-[9px] font-black px-2 py-0.5 rounded-md border uppercase whitespace-nowrap bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20">
                                    主驱动 {aiData.dominant_driver}
                                </span>
                            )}
                            {aiData.trade_setup_status && (
                                <span className="text-[9px] font-black px-2 py-0.5 rounded-md border uppercase whitespace-nowrap bg-violet-50 text-violet-600 border-violet-200 dark:bg-violet-600/10 dark:text-violet-400 dark:border-violet-600/20">
                                    {aiData.trade_setup_status}
                                </span>
                            )}
                            {selectedItem.market_status === "PRE_MARKET" && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-orange-200 bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/20 ml-1">
                                    <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘前 PRE</span>
                                </div>
                            )}
                            {selectedItem.market_status === "AFTER_HOURS" && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-slate-200 bg-slate-50 text-slate-500 dark:bg-slate-500/10 dark:text-slate-400 dark:border-slate-500/20 ml-1">
                                    <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘后 POST</span>
                                </div>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-sm font-semibold text-blue-600 dark:text-blue-600 opacity-90">
                                {heroSubtitle || aiData.summary_status || "技术修复中"}
                            </span>
                            
                            {/* 加入模拟交易按钮 */}
                            {(aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多")) && (
                                <Button
                                    size="sm"
                                    onClick={handleJoinPaperTrade}
                                    disabled={isCreatingTrade || tradeCreated}
                                    className={clsx(
                                        "h-7 px-3 text-[10px] font-bold rounded-lg transition-all",
                                        tradeCreated 
                                            ? "bg-emerald-600 text-white hover:bg-emerald-600" 
                                            : "bg-blue-600 text-white hover:bg-blue-700 hover:scale-105 active:scale-95 shadow-sm shadow-blue-600/20"
                                    )}
                                >
                                    {tradeCreated ? (
                                        <span className="flex items-center gap-1"><ShieldCheck className="h-3 w-3" /> 已加入</span>
                                    ) : isCreatingTrade ? (
                                        "创建中..."
                                    ) : (
                                        <span className="flex items-center gap-1"><Play className="h-3 w-3 fill-white" /> 模拟买入</span>
                                    )}
                                </Button>
                            )}
                        </div>
                        {shouldShowActionReason && (
                            <div className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 px-3 py-2">
                                <p className="text-[11px] font-medium leading-relaxed text-slate-600 dark:text-slate-300">
                                    {actionReason}
                                </p>
                            </div>
                        )}

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                            <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                <Clock className="h-3 w-3 text-blue-400" />
                                期限：<span className="text-slate-900 dark:text-slate-200">{aiData.investment_horizon || "中期"}</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                <Zap className="h-3 w-3 text-blue-400" />
                                信心：<span className="text-slate-900 dark:text-slate-200">{aiData.confidence_level || "72"}%</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                <AlertCircle className="h-3 w-3 text-blue-400" />
                                风险：<span className="text-slate-900 dark:text-slate-200">{aiData.risk_level || "中"}</span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Sentiment Bias */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-center text-[11px] font-black uppercase text-slate-400 tracking-[0.3em]">
                            <div className="flex items-center gap-3">
                                <Activity className="h-4 w-4 text-blue-600" />
                                <span>AI 情绪偏差</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-slate-900 dark:text-white font-black italic">{aiData.sentiment_score || 58}%</span>
                                <span className={clsx(
                                    "px-2 py-0.5 rounded-md border text-[9px] font-black uppercase",
                                    (aiData.sentiment_score || 0) > 60 ? "bg-emerald-50 text-emerald-600 border-emerald-200" :
                                        (aiData.sentiment_score || 0) < 40 ? "bg-rose-50 text-rose-600 border-rose-200" :
                                            "bg-blue-50 text-blue-600 border-blue-200"
                                )}>
                                    {aiData.sentiment_score && aiData.sentiment_score > 60 ? "Bullish" :
                                        aiData.sentiment_score && aiData.sentiment_score < 40 ? "Bearish" : "Neutral"}
                                </span>
                            </div>
                        </div>
                        <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0">
                            <div
                                className="h-full rounded-full bg-blue-600 animate-[grow-bar_1.2s_cubic-bezier(0.22,1,0.36,1)_forwards]"
                                style={{ width: `${aiData.sentiment_score || 58}%`, ['--bar-width' as string]: `${aiData.sentiment_score || 58}%` }}
                            />
                        </div>
                        <div className="flex justify-between text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                            <span>0: 极度看空</span>
                            <span className="text-center">50: 中性</span>
                            <span className="text-right">100: 极度看多</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. Trade Range Axis */}
            <div className="py-4 px-6 space-y-3">
                <div className="space-y-3">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <div className="text-sm font-black uppercase text-blue-600 dark:text-blue-600 tracking-[0.1em] flex items-center gap-2">
                                <Target className="h-4 w-4 text-blue-600" />
                                <span>交易执行区间</span>
                            </div>
                            <p className="text-[10px] font-medium text-slate-400 italic opacity-80 ml-6">* 基于当前价的深度研判</p>
                        </div>
                        <div className="flex gap-3">
                            <div className="flex flex-col items-end gap-0.5 bg-rose-50/80 dark:bg-rose-600/5 border border-rose-100 dark:border-rose-600/10 rounded-xl px-3 py-1.5">
                                <span className="text-[9px] font-black text-rose-400 dark:text-rose-600/80 uppercase tracking-tighter">
                                    {(selectedItem?.quantity || 0) > 0 ? "止损" : "预设止损"}
                                </span>
                                <span className={clsx(
                                    "text-md font-black tabular-nums",
                                    (selectedItem?.quantity || 0) > 0 ? "text-rose-600 dark:text-rose-400" : "text-rose-400 dark:text-rose-600/80"
                                )}>
                                    ${aiData.stop_loss_price?.toFixed(2) || "--"}
                                </span>
                            </div>
                            <div className="flex flex-col items-end gap-0.5 bg-emerald-50/80 dark:bg-emerald-600/5 border border-emerald-100 dark:border-emerald-600/10 rounded-xl px-3 py-1.5">
                                <span className="text-[9px] font-black text-emerald-400 dark:text-emerald-600/80 uppercase tracking-tighter">建仓区间</span>
                                <span className="text-md font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                                    {aiData.entry_price_low != null && aiData.entry_price_high != null
                                        ? `$${aiData.entry_price_low.toFixed(2)} - $${aiData.entry_price_high.toFixed(2)}`
                                        : (aiData.entry_zone || "--")
                                    }
                                </span>
                            </div>
                            <div className="flex flex-col items-end gap-0.5 bg-blue-50/80 dark:bg-blue-600/5 border border-blue-100 dark:border-blue-600/10 rounded-xl px-3 py-1.5">
                                <span className="text-[9px] font-black text-blue-400 dark:text-blue-600/80 uppercase tracking-tighter">目标止盈</span>
                                <span className="text-md font-black text-blue-600 dark:text-blue-400 tabular-nums">${aiData.target_price?.toFixed(2) || "--"}</span>
                            </div>
                        </div>
                    </div>

                    {/* Visual Axis Line */}
                    <TradeAxisVisual
                        selectedItem={selectedItem}
                        aiData={aiData}
                        sanitizePrice={sanitizePrice}
                    />
                </div>
            </div>

            {/* 3. Core Logic Summary (NEW) */}
            {aiData.core_logic_summary && (
                <div className="py-2 px-6">
                    <div className="bg-blue-50/30 dark:bg-blue-900/10 border border-blue-100/50 dark:border-blue-900/20 rounded-2xl p-4 space-y-2">
                        <div className="flex items-center gap-2 text-[11px] font-black uppercase text-blue-600/80 tracking-wider">
                            <LayoutDashboard className="h-3.5 w-3.5" />
                            <span>核心研判摘要</span>
                        </div>
                        <p className="text-[13px] font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                            {aiData.core_logic_summary}
                        </p>
                    </div>
                </div>
            )}

            {/* 4. Decision Brief */}
            {(aiData.trigger_condition || aiData.invalidation_condition || aiData.next_review_point || aiData.add_on_trigger || aiData.max_position_pct != null) && (
                <div className="px-6 py-2">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                        <DecisionBriefCard
                            title="计划生效"
                            value={aiData.trigger_condition}
                            icon={<Target className="h-3.5 w-3.5" />}
                            tone="blue"
                        />
                        <DecisionBriefCard
                            title="计划失效"
                            value={aiData.invalidation_condition}
                            icon={<AlertCircle className="h-3.5 w-3.5" />}
                            tone="rose"
                        />
                        <DecisionBriefCard
                            title="加仓触发"
                            value={aiData.add_on_trigger}
                            icon={<TrendingUp className="h-3.5 w-3.5" />}
                            tone="emerald"
                        />
                        <DecisionBriefCard
                            title="复核点"
                            value={aiData.next_review_point}
                            icon={<Clock className="h-3.5 w-3.5" />}
                            tone="slate"
                        />
                    </div>
                    {aiData.max_position_pct != null && (
                        <div className="mt-3 flex items-center gap-2 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                            <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
                            <span>最大仓位建议</span>
                            <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 tabular-nums">
                                {aiData.max_position_pct.toFixed(0)}%
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* 5. Scenario Panel */}
            {(aiData.bull_case || aiData.base_case || aiData.bear_case) && (
                <div className="px-6 py-2">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <ScenarioCard title="乐观情景" value={aiData.bull_case} tone="emerald" />
                        <ScenarioCard title="基准情景" value={aiData.base_case} tone="blue" />
                        <ScenarioCard title="悲观情景" value={aiData.bear_case} tone="rose" />
                    </div>
                </div>
            )}

            {/* 6. Logical Breakdown - Collapsable */}
            <div className="border-t border-slate-100 dark:border-white/5">
                <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full py-4 px-6 flex items-center justify-between group hover:bg-slate-50/50 dark:hover:bg-white/5 transition-colors"
                >
                    <div className="text-sm font-black uppercase text-blue-600 dark:text-blue-600 tracking-[0.1em] flex items-center gap-2">
                        <Activity className="h-4 w-4 text-blue-600" />
                        <span>详细诊断研判逻辑</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 group-hover:text-blue-500 transition-colors uppercase tracking-widest">
                        {isExpanded ? "收起详情" : "查看完整分析"}
                        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                </button>
                
                {isExpanded && (
                    <div className="px-6 pb-6 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                        <div className="prose dark:prose-invert max-w-none text-[13px] font-normal leading-relaxed text-slate-500 dark:text-slate-400 [&>p]:m-0">
                            <MarkdownWithRefs content={aiData.action_advice || ""} />
                        </div>
                    </div>
                )}
            </div>

            {/* 7. Footer: Disclaimer + Version */}
            <div className="px-6 py-2.5 bg-slate-50/80 dark:bg-zinc-900/80 rounded-b-3xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-1.5">
                    <div className="flex items-center gap-1.5 text-[8px] leading-relaxed text-slate-300 dark:text-slate-600 font-medium">
                        <span className="font-black text-orange-500/60 dark:text-orange-500/40 italic shrink-0">DISCLAIMER:</span>
                        <span>本报告基于机器学习算法自动化生成，不构成投资建议。价格建议仅供参考，不对盈亏负责。投资有风险，操作须谨慎。</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        <ShieldCheck className="h-2.5 w-2.5 text-slate-300 dark:text-slate-600" />
                        <span className="text-[8px] font-bold text-slate-300 dark:text-slate-600 uppercase tracking-widest whitespace-nowrap">
                            AI V4.0 • {(aiData.model_used || "UNKNOWN").toUpperCase()} • <span suppressHydrationWarning>{aiData.created_at ? formatDistanceToNow(new Date(aiData.created_at + (aiData.created_at.includes('Z') ? '' : 'Z')), { addSuffix: true, locale: zhCN }) : ''}</span>
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DecisionBriefCard({
    title,
    value,
    icon,
    tone,
}: {
    title: string;
    value?: string;
    icon: React.ReactNode;
    tone: "blue" | "rose" | "emerald" | "slate";
}) {
    if (!value) {
        return null;
    }

    const toneClass = {
        blue: "border-blue-100 bg-blue-50/40 text-blue-600 dark:border-blue-900/20 dark:bg-blue-900/10 dark:text-blue-400",
        rose: "border-rose-100 bg-rose-50/40 text-rose-600 dark:border-rose-900/20 dark:bg-rose-900/10 dark:text-rose-400",
        emerald: "border-emerald-100 bg-emerald-50/40 text-emerald-600 dark:border-emerald-900/20 dark:bg-emerald-900/10 dark:text-emerald-400",
        slate: "border-slate-100 bg-slate-50/60 text-slate-600 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-300",
    }[tone];

    return (
        <div className={clsx("rounded-2xl border px-4 py-3 space-y-2", toneClass)}>
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em]">
                {icon}
                <span>{title}</span>
            </div>
            <p className="text-[13px] leading-relaxed font-medium text-slate-700 dark:text-slate-200">
                {compactSentence(value, 44)}
            </p>
        </div>
    );
}

function ScenarioCard({
    title,
    value,
    tone,
}: {
    title: string;
    value?: string;
    tone: "emerald" | "blue" | "rose";
}) {
    if (!value) {
        return null;
    }

    const toneClass = {
        emerald: "border-emerald-100 bg-emerald-50/30 dark:border-emerald-900/20 dark:bg-emerald-900/10",
        blue: "border-blue-100 bg-blue-50/30 dark:border-blue-900/20 dark:bg-blue-900/10",
        rose: "border-rose-100 bg-rose-50/30 dark:border-rose-900/20 dark:bg-rose-900/10",
    }[tone];

    const titleClass = {
        emerald: "text-emerald-600 dark:text-emerald-400",
        blue: "text-blue-600 dark:text-blue-400",
        rose: "text-rose-600 dark:text-rose-400",
    }[tone];

    const { trigger, action } = splitScenario(value);

    return (
        <div className={clsx("rounded-2xl border px-4 py-3 space-y-2", toneClass)}>
            <div className={clsx("text-[10px] font-black uppercase tracking-[0.18em]", titleClass)}>
                {title}
            </div>
            <div className="space-y-2">
                {trigger && (
                    <div className="space-y-1">
                        <div className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                            触发条件
                        </div>
                        <p className="text-[13px] leading-relaxed font-medium text-slate-700 dark:text-slate-200">
                            {compactSentence(trigger, 52)}
                        </p>
                    </div>
                )}
                {action && (
                    <div className="space-y-1">
                        <div className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                            对应动作
                        </div>
                        <p className="text-[13px] leading-relaxed font-medium text-slate-700 dark:text-slate-200">
                            {compactSentence(action, 52)}
                        </p>
                    </div>
                )}
                {!trigger && !action && (
                    <p className="text-[13px] leading-relaxed font-medium text-slate-700 dark:text-slate-200">
                        {compactSentence(value, 64)}
                    </p>
                )}
            </div>
        </div>
    );
}

// ========================================
// 交易轴可视化子组件 (Trade Axis Visual)
// ========================================

function TradeAxisVisual({
    selectedItem,
    aiData,
    sanitizePrice
}: {
    selectedItem: AIVerdictProps["selectedItem"];
    aiData: NonNullable<AIVerdictProps["aiData"]>;
    sanitizePrice: (val: number | null | undefined) => string;
}) {
    if (!aiData || !aiData.stop_loss_price || !aiData.target_price || !selectedItem) return null;

    const stop = aiData.stop_loss_price;
    const target = aiData.target_price;
    const strategyRange = target - stop;
    const buffer = strategyRange * 0.2;

    let axisMin = stop - buffer;
    let axisMax = target + buffer;

    const current = selectedItem.current_price;
    if (current < axisMin) axisMin = current - buffer;
    if (current > axisMax) axisMax = current + buffer;

    const totalRange = axisMax - axisMin;
    const getPos = (val: number) => ((val - axisMin) / totalRange) * 100;

    const stopPrice = aiData.stop_loss_price;
    const entryLow = aiData.entry_price_low || stopPrice;
    const entryHigh = aiData.entry_price_high || entryLow;
    const targetPrice = aiData.target_price;

    const isHolding = (selectedItem?.quantity || 0) > 0;

    // 核心：过滤掉重复或无效的区间
    const rawZones = [
        { name: isHolding ? "止损" : "预设止损", start: axisMin, end: stopPrice, color: isHolding ? "bg-rose-600 dark:bg-rose-600/80" : "bg-[repeating-linear-gradient(45deg,transparent,transparent_4px,rgba(244,63,94,0.5)_4px,rgba(244,63,94,0.5)_8px)] opacity-90 border-y border-rose-600/40" },
        { name: "观察", start: stopPrice, end: entryLow, color: "bg-[#E8EAED] dark:bg-white/5 opacity-30" },
        { name: "买入", start: entryLow, end: entryHigh, color: "bg-emerald-600 dark:bg-emerald-600/80" },
        { name: "持有", start: entryHigh, end: targetPrice, color: "bg-[#E8EAED] dark:bg-white/10" },
        { name: "止盈", start: targetPrice, end: axisMax, color: "bg-blue-600 dark:bg-blue-600/80" }
    ];

    const visibleZones = rawZones.filter(z => z.end > z.start);

    // 生成关键价位刻度
    const keyPrices = [
        { val: stopPrice, label: "止损" },
        { val: entryLow, label: "建仓" },
        { val: entryHigh, label: "加码" },
        { val: targetPrice, label: "目标" }
    ].filter((item, index, self) =>
        index === self.findIndex((t) => Math.abs(t.val - item.val) < 0.01)
    ).sort((a, b) => a.val - b.val);

    return (
        <div className="relative pt-12 pb-2">
            <div className="relative">
                {/* Main Bar Container */}
                <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0">
                    <div className="h-full w-full flex overflow-hidden">
                        {visibleZones.map((zone, idx) => (
                            <div
                                key={idx}
                                className={clsx("h-full", zone.color)}
                                style={{ width: `${((zone.end - zone.start) / totalRange) * 100}%` }}
                            />
                        ))}
                    </div>
                </div>

                {/* Tooltip & Marker Dot Group */}
                <div
                    className="absolute top-1/2 -translate-y-1/2 z-20 flex flex-col items-center"
                    style={{ left: `${getPos(current)}%`, transition: 'left 0.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
                >
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 flex flex-col items-center">
                        <div className="bg-slate-900 dark:bg-black text-white text-[10px] font-black px-2.5 py-1 rounded-lg shadow-2xl border border-white/10 whitespace-nowrap">
                            ${sanitizePrice(current)}
                        </div>
                        <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-t-[4px] border-l-transparent border-r-transparent border-t-slate-900 dark:border-t-black -mt-px" />
                    </div>

                    {/* Marker Dot */}
                    <div className="w-4 h-4 bg-blue-600 rounded-full border-[3px] border-white dark:border-slate-950 shadow-lg ring-4 ring-blue-600/10" />
                </div>
            </div>

            {/* Key Price Labels */}
            <div className="relative h-6 mt-4">
                {keyPrices.map((tick, i) => (
                    <div
                        key={i}
                        className="absolute flex flex-col items-center -translate-x-1/2"
                        style={{ left: `${getPos(tick.val)}%` }}
                    >
                        <div className="w-px h-1.5 bg-slate-200 dark:bg-slate-700 mb-1" />
                        <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 tabular-nums">
                            {tick.val.toFixed(2)}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ========================================
// 信号追踪与复盘 (Truth Tracker)
// ========================================

function TruthTracker({
    analysisHistory,
    selectedItem
}: {
    analysisHistory: AIVerdictProps["analysisHistory"];
    selectedItem: AIVerdictProps["selectedItem"];
}) {
    return (
        <div className="bg-slate-50/50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2rem] p-6">
            <div className="flex items-center gap-3 mb-6">
                <Clock className="h-5 w-5 text-blue-600" />
                <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">AI 信号追踪与复盘 (The Truth Tracker)</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisHistory.slice(0, 3).map((report, idx) => {
                    const hPrice = report.history_price;
                    const cPrice = selectedItem.current_price;
                    const pl = hPrice ? ((cPrice - hPrice) / hPrice) * 100 : null;
                    const isWin = report.immediate_action?.includes("买") ? (pl !== null && pl > 0) :
                        report.immediate_action?.includes("卖") ? (pl !== null && pl < 0) : null;

                    return (
                        <div key={idx} className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 p-4 rounded-2xl shadow-sm hover:shadow-md transition-shadow group relative overflow-hidden">
                            {isWin !== null && (
                                <div className={clsx(
                                    "absolute top-0 right-0 px-3 py-1 text-[8px] font-black uppercase rounded-bl-xl",
                                    isWin ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"
                                )}>
                                    {isWin ? "命中" : "回撤"}
                                </div>
                            )}

                            <div className="flex justify-between items-start mb-3">
                                <div className="flex flex-col">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter" suppressHydrationWarning>
                                        {report.created_at ? format(new Date(report.created_at + (report.created_at.includes('Z') ? '' : 'Z')), "MMM dd, yyyy", { locale: zhCN }) : "--"}
                                    </span>
                                    <span className={clsx(
                                        "text-xs font-black uppercase mt-1",
                                        report.immediate_action?.includes("买") ? "text-emerald-600" :
                                            report.immediate_action?.includes("卖") ? "text-rose-600" : "text-slate-500"
                                    )}>
                                        {report.immediate_action || "--"}
                                    </span>
                                </div>
                                <div className="flex flex-col items-end">
                                    <span className="text-[8px] font-bold text-slate-400 uppercase">建仓时价</span>
                                    <span className="text-xs font-black tabular-nums text-slate-700 dark:text-slate-300">
                                        ${hPrice?.toFixed(2) || "--"}
                                    </span>
                                </div>
                            </div>

                            <div className="flex items-center justify-between border-t border-slate-50 dark:border-zinc-800 pt-3">
                                <div className="flex flex-col">
                                    <span className="text-[8px] font-bold text-slate-400 uppercase">预期盈亏</span>
                                    <span className={clsx(
                                        "text-sm font-black tabular-nums",
                                        pl && pl >= 0 ? "text-emerald-600" : "text-rose-600"
                                    )}>
                                        {pl !== null ? `${pl >= 0 ? "+" : ""}${pl.toFixed(2)}%` : "--"}
                                    </span>
                                </div>
                                <div className="flex gap-1.5 overflow-hidden">
                                    <span className="text-[8px] font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded uppercase">
                                        {String(report.risk_level || "中")}险
                                    </span>
                                    <span className="text-[8px] font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded uppercase">
                                        {String(report.confidence_level || "70")}%信心
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
