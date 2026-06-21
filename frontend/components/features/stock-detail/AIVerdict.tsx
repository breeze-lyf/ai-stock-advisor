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
    BarChart3, AlertCircle,
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
                    <h2 className="text-xl font-black tracking-tight text-neutral-900 dark:text-neutral-100 uppercase">AI 判研与交易计划</h2>
                </div>
                <div className="flex flex-col items-center">
                    <Button
                        onClick={() => onAnalyze(true)}
                        disabled={analyzing}
                        className="bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 font-black px-6 h-10 rounded-xl hover:scale-105 transition-transform active:scale-95 mr-4 md:mr-10"
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

            {/* 内容区 */}
            <div>
                {aiData ? (
                    <AIVerdictContent
                        selectedItem={selectedItem}
                        aiData={aiData}
                        analysisHistory={analysisHistory}
                        currency={currency}
                        sanitizePrice={sanitizePrice}
                    />
                ) : (
                    <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed border-neutral-100 dark:border-neutral-800 rounded-[2rem] text-neutral-400 gap-4">
                        <BarChart3 className="h-10 w-10 opacity-10" />
                        <p className="text-[10px] font-bold uppercase tracking-[0.3em]">等待诊断报告生成...</p>
                    </div>
                )}

                {/* AI 历史信号复盘 (Signal Tracker) */}
                {analysisHistory.length > 0 && (
                    <div className="mt-3 animate-in fade-in slide-in-from-bottom-4 duration-1000">
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

function forceCompactHeroTitle(value: string) {
    return value
        .replace(/等待/gu, "等待 ")
        .replace(/确认/gu, "确认 ")
        .replace(/回踩/gu, "回踩 ")
        .replace(/\s+/g, " ")
        .trim();
}

function buildHeroHeadline(immediateAction?: string, triggerCondition?: string) {
    const raw = (immediateAction || "观望").replace(/\s+/g, "").trim();
    if (!raw) return "观望";
    if (raw.length <= 8) return raw;

    if (raw.includes("观望") && (raw.includes("突破") || raw.includes("回踩") || raw.includes("触发"))) {
        return "观望/等待触发";
    }
    if (raw.includes("低吸")) {
        return raw.includes("观望") ? "观望/低吸" : "低吸布局";
    }
    if (raw.includes("持有") && raw.includes("加仓")) {
        return "持有/等待加仓";
    }
    if (raw.includes("减仓") || raw.includes("止盈")) {
        return "减仓/兑现";
    }
    if (raw.includes("买入") || raw.includes("建仓")) {
        return raw.includes("回踩") ? "回踩/分批建仓" : "分批建仓";
    }
    if (raw.includes("观望") && triggerCondition) {
        return "观望/等待触发";
    }

    return forceCompactHeroTitle(raw);
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
    const [isExpanded, setIsExpanded] = React.useState(true);
    
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
        { name: "观望/持有", start: entryHigh, end: target, color: "bg-[#E8EAED] dark:bg-neutral-600", darkColor: "bg-neutral-600", textColor: "text-neutral-500 dark:text-neutral-400", bgColor: "bg-neutral-50 dark:bg-neutral-800/50", borderColor: "border-neutral-200 dark:border-neutral-700" },
        { name: "止盈", start: target, end: axisMax, color: "bg-blue-600", darkColor: "bg-blue-600/80", textColor: "text-blue-600 dark:text-blue-400", bgColor: "bg-blue-50 dark:bg-blue-600/10", borderColor: "border-blue-200 dark:border-blue-600/20" }
    ];

    const activeZone = zones.find(z => current >= z.start && current <= z.end) ||
        (current < axisMin ? zones[0] : zones[zones.length - 1]);

    // 计划盈亏比：从数据库持久化字段读取（基于建仓区间中位价，反映策略本身的质量）
    const effectiveRR = selectedItem?.target_risk_reward_ratio?.toFixed(2) || aiData.rr_ratio;
    // 实时盈亏比：以此刻股价为入场基准，反映"现在买合不合适"
    const liveRR: string | null = (() => {
        if (!target || !stop || !current || current <= stop) return null;
        const reward = target - current;
        const risk = current - stop;
        if (reward <= 0 || risk <= 0) return null;
        return (reward / risk).toFixed(2);
    })();
    const { title: heroTitle, subtitle: heroSubtitle } = splitHeroTitle(aiData.immediate_action, aiData.trigger_condition);
    const actionReason = aiData.trade_setup_status === "接近触发"
        ? `当前不直接执行：${compactSentence(aiData.trigger_condition || aiData.core_logic_summary, 42)}`
        : aiData.trade_setup_status === "未触发"
            ? `当前先观察：${compactSentence(aiData.trigger_condition || aiData.core_logic_summary, 42)}`
            : "";
    const shouldShowActionReason = Boolean(actionReason) && !heroSubtitle && (
        normalizeComparisonText(actionReason) !== normalizeComparisonText(heroSubtitle)
    );
    const reviewPoint = aiData.next_review_point || "待后续事件复核";
    const createdLabel = aiData.created_at
        ? formatDistanceToNow(new Date(aiData.created_at + (aiData.created_at.includes("Z") ? "" : "Z")), { addSuffix: true, locale: zhCN })
        : "";
    const compactHeroTitle = buildHeroHeadline(heroTitle, aiData.trigger_condition);

    return (
        <div className="space-y-8">

            {/* 模块1：AI 判研与交易计划 */}
            <div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] overflow-hidden">

            {/* 1. Header & Sentiment Grid */}
            <div className="py-4 px-6 md:py-6 md:px-8 bg-neutral-50/50 dark:bg-white/5 border-b border-neutral-100 dark:border-white/5">
                <div className="space-y-4">
                    <div className="space-y-3 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className={clsx(
                                "min-w-0 text-[34px] leading-[0.94] md:text-[38px] md:leading-[0.92] font-black tracking-tight break-words",
                                aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多") ? "text-neutral-900 dark:text-white" :
                                    aiData.immediate_action?.includes("卖") || aiData.immediate_action?.includes("减") ? "text-rose-600 dark:text-rose-400" :
                                        "text-neutral-900 dark:text-white"
                            )}>
                                {compactHeroTitle}
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
                                "flex items-center gap-1.5 px-2 py-0.5 rounded-md border",
                                parseFloat(effectiveRR || "0") >= 2.5 ? "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-600/10 dark:text-emerald-400 dark:border-emerald-600/20" :
                                    parseFloat(effectiveRR || "0") >= 1.8 ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20" :
                                        "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-600/10 dark:text-rose-400 dark:border-rose-600/20"
                            )} title="计划盈亏比：基于建仓区间中位价，反映策略本身的质量">
                                <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70">计划 R/R</span>
                                <span className="text-[10px] font-black tabular-nums">{effectiveRR || "--"}</span>
                            </div>
                            {liveRR !== null && (
                                <div className={clsx(
                                    "flex items-center gap-1.5 px-2 py-0.5 rounded-md border",
                                    parseFloat(liveRR) >= 2.5 ? "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-600/10 dark:text-emerald-400 dark:border-emerald-600/20" :
                                        parseFloat(liveRR) >= 1.8 ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20" :
                                            "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-600/10 dark:text-amber-400 dark:border-amber-600/20"
                                )} title="实时盈亏比：基于当前价格，反映此刻买入的性价比">
                                    <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70">当前 R/R</span>
                                    <span className="text-[10px] font-black tabular-nums">{liveRR}</span>
                                </div>
                            )}
                            {aiData.dominant_driver && (
                                <span className="text-[9px] font-black px-2 py-0.5 rounded-md border uppercase whitespace-nowrap bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20">
                                    主驱动 {aiData.dominant_driver}
                                </span>
                            )}
                            {selectedItem.market_status === "PRE_MARKET" && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-orange-200 bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/20">
                                    <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘前 PRE</span>
                                </div>
                            )}
                            {selectedItem.market_status === "AFTER_HOURS" && (
                                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-neutral-200 bg-neutral-50 text-neutral-500 dark:bg-neutral-500/10 dark:text-neutral-400 dark:border-neutral-500/20">
                                    <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘后 POST</span>
                                </div>
                            )}
                        </div>

                        {(heroSubtitle || aiData.summary_status) && (
                            <div className="flex items-start gap-2.5 pl-3 border-l-[3px] border-blue-500 py-1">
                                <div className="flex-1 min-w-0">
                                    <div className="text-[10px] font-black text-blue-700 uppercase tracking-wider mb-0.5">
                                        等待触发
                                    </div>
                                    <p className="text-[15px] font-bold text-neutral-900 dark:text-neutral-100 leading-snug">
                                        {heroSubtitle || aiData.summary_status}
                                    </p>
                                </div>
                                {aiData.trade_setup_status && (
                                    <span className="shrink-0 text-[9px] font-black px-2 py-1 rounded-md border uppercase whitespace-nowrap bg-violet-50 text-violet-600 border-violet-200 dark:bg-violet-600/10 dark:text-violet-400 dark:border-violet-600/20">
                                        {aiData.trade_setup_status}
                                    </span>
                                )}
                            </div>
                        )}

                        {shouldShowActionReason && (
                            <div className="rounded-xl bg-neutral-50 dark:bg-neutral-950 border border-neutral-100 dark:border-neutral-800 px-3 py-2">
                                <p className="text-[11px] font-medium leading-relaxed text-neutral-600 dark:text-neutral-300">
                                    {actionReason}
                                </p>
                            </div>
                        )}

                        <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500 font-medium pt-1">
                            <span className="flex items-center gap-1"><span className="text-neutral-400">期限</span><span className="text-neutral-700 dark:text-neutral-200 font-semibold">{aiData.investment_horizon || "1-2 周"}</span></span>
                            <span className="text-neutral-200 dark:text-neutral-700">·</span>
                            <span className="flex items-center gap-1"><span className="text-neutral-400">风险</span><span className="text-amber-600 dark:text-amber-400 font-semibold">{aiData.risk_level || "中"}</span></span>
                            <span className="text-neutral-200 dark:text-neutral-700">·</span>
                            <span className="flex items-center gap-1"><span className="text-neutral-400">下次复核</span><span className="text-neutral-700 dark:text-neutral-200 font-semibold">{reviewPoint}</span></span>
                            {createdLabel && (
                                <span className="ml-auto text-[10px] text-neutral-400">已分析 {createdLabel}</span>
                            )}
                        </div>

                        {(aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多")) && (
                            <div className="flex items-center gap-3">
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
                            </div>
                        )}
                    </div>

                    {aiData.confidence_breakdown && Object.values(aiData.confidence_breakdown).some(v => v != null) && (
                        <div className="pt-4">
                            <InlineConfidenceBreakdown
                                confidenceLevel={aiData.confidence_level}
                                breakdown={aiData.confidence_breakdown}
                                technicalRationale={aiData.technical_analysis}
                                fundamentalRationale={aiData.fundamental_analysis}
                                macroRationale={aiData.macro_risk_note}
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* 2. Trade Range Axis */}
            <div className="py-4 px-6 space-y-3">
                <div className="space-y-3">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <div className="text-sm font-black uppercase text-blue-600 dark:text-blue-600 tracking-widest flex items-center gap-2">
                                <Target className="h-4 w-4 text-blue-600" />
                                <span>交易执行区间</span>
                            </div>
                            <p className="text-[10px] font-medium text-neutral-400 italic opacity-80 ml-6">* 基于当前价的深度研判</p>
                        </div>
                    </div>

                    {/* Visual Axis Line */}
                    <TradeAxisVisual
                        selectedItem={selectedItem}
                        aiData={aiData}
                        sanitizePrice={sanitizePrice}
                    />

                    {/* Detailed Trading Cards */}
                    <TradeExecutionDetails
                        aiData={aiData}
                        currentPrice={current}
                        stop={stop}
                        entryLow={entryLow}
                        entryHigh={entryHigh}
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
                        <p className="text-[13px] font-medium leading-relaxed text-neutral-700 dark:text-neutral-300">
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
                        <div className="mt-3 flex items-center gap-2 text-[11px] font-bold text-neutral-500 uppercase tracking-widest">
                            <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
                            <span>最大仓位建议</span>
                            <span className="px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 tabular-nums">
                                {aiData.max_position_pct.toFixed(0)}%
                            </span>
                        </div>
                    )}
                </div>
            )}

            </div>{/* end 模块1 */}

            {/* 模块2：深度论据（含块5 情景、块6 详细诊断）*/}
            <div className="flex items-center gap-3 mb-4">
                <div className="h-8 w-1.5 bg-violet-600 rounded-full shadow-[0_0_12px_rgba(124,58,237,0.5)]" />
                <h2 className="text-xl font-black tracking-tight text-neutral-900 dark:text-neutral-100 uppercase">深度论据</h2>
            </div>
            <div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] overflow-hidden">

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
            <div className="px-6 pb-6">
                <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full rounded-[22px] border border-neutral-200 bg-neutral-50/80 px-5 py-4 flex items-center justify-between group hover:bg-neutral-100/80 dark:border-zinc-800 dark:bg-zinc-950/70 dark:hover:bg-zinc-900 transition-colors"
                >
                    <div className="text-sm font-black uppercase text-blue-600 dark:text-blue-600 tracking-widest flex items-center gap-2">
                        <Activity className="h-4 w-4 text-blue-600" />
                        <span>详细诊断研判逻辑</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-neutral-400 group-hover:text-blue-500 transition-colors uppercase tracking-widest">
                        {isExpanded ? "收起详情" : "查看完整分析"}
                        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                </button>
                
                {isExpanded && (
                    <div className="mt-3 px-1 py-2 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                        <div className="prose dark:prose-invert max-w-none text-[13px] font-normal leading-relaxed text-neutral-500 dark:text-neutral-400 [&>p]:m-0">
                            <MarkdownWithRefs content={aiData.action_advice || ""} />
                        </div>
                    </div>
                )}
            </div>

            </div>{/* end 模块2 */}

        </div>
    );
}

// ========================================
// Inline Confidence Breakdown (replaces sentiment bar when AI returns breakdown data)
// ========================================
const CONF_DIMS = [
    { key: "technical" as const, label: "技术面", color: "bg-cyan-500", textColor: "text-cyan-600 dark:text-cyan-400", rationaleKey: "technical" as const },
    { key: "fundamental" as const, label: "基本面", color: "bg-blue-500", textColor: "text-blue-600 dark:text-blue-400", rationaleKey: "fundamental" as const },
    { key: "macro" as const, label: "宏观面", color: "bg-amber-500", textColor: "text-amber-600 dark:text-amber-400", rationaleKey: "macro" as const },
];

const RATIONALE_SOURCES = {
    technical: (d: { technicalRationale?: string }) => d.technicalRationale,
    fundamental: (d: { fundamentalRationale?: string }) => d.fundamentalRationale,
    macro: (d: { macroRationale?: string }) => d.macroRationale,
} as const;

function extractRationale(text?: string, maxLen = 50): string {
    if (!text) return "";
    const normalized = text.replace(/\s+/g, " ").trim();
    return normalized.length <= maxLen ? normalized : normalized.slice(0, maxLen) + "...";
}

function InlineConfidenceBreakdown({
    confidenceLevel,
    breakdown,
    technicalRationale,
    fundamentalRationale,
    macroRationale,
}: {
    confidenceLevel?: number;
    breakdown?: { technical?: number; fundamental?: number; macro?: number; sentiment?: number };
    technicalRationale?: string;
    fundamentalRationale?: string;
    macroRationale?: string;
}) {
    return (
        <div className="space-y-3">
            <div className="flex items-center gap-2">
                <span className="text-[10px] font-black text-neutral-400 uppercase tracking-wider">信心构成分解</span>
                <span className="text-[9px] font-black px-1.5 py-0.5 rounded border bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20">
                    NEW
                </span>
                {confidenceLevel != null && (
                    <div className="text-[10px] text-neutral-400 ml-auto">
                        总信心{" "}
                        <span className={clsx(
                            "font-bold",
                            confidenceLevel >= 70 ? "text-neutral-700 dark:text-neutral-200" : confidenceLevel >= 45 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"
                        )}>
                            {confidenceLevel}%
                        </span>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-3 gap-3">
                {CONF_DIMS.map(({ key, label, color, textColor, rationaleKey }) => {
                    const val = breakdown?.[key];
                    if (val == null) return null;
                    const sourceFn = RATIONALE_SOURCES[rationaleKey];
                    const rationale = extractRationale(sourceFn({ technicalRationale, fundamentalRationale, macroRationale } as never));

                    const dimColors: Record<string, { bg: string; border: string }> = {
                        technical: { bg: "bg-emerald-50 dark:bg-emerald-600/10", border: "border-emerald-100 dark:border-emerald-600/20" },
                        fundamental: { bg: "bg-blue-50 dark:bg-blue-600/10", border: "border-blue-100 dark:border-blue-600/20" },
                        macro: { bg: "bg-amber-50 dark:bg-amber-600/10", border: "border-amber-100 dark:border-amber-600/20" },
                    };

                    return (
                        <div key={key} className={clsx("rounded-xl p-3 border", dimColors[rationaleKey]?.bg, dimColors[rationaleKey]?.border)}>
                            <div className="flex items-center justify-between mb-2">
                                <span className={clsx("text-[10px] font-black uppercase", textColor)}>{label}</span>
                                <span className={clsx("text-sm font-black tabular-nums", textColor)}>{val}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-white/50 dark:bg-black/20 rounded-full overflow-hidden">
                                <div
                                    className={clsx("h-full rounded-full transition-all duration-700", color)}
                                    style={{ width: `${Math.min(100, Math.max(0, val))}%` }}
                                />
                            </div>
                            <p className={clsx("text-[10px] mt-2 leading-relaxed", textColor)}>
                                {rationale || "等待更多结构化依据补充"}
                            </p>
                        </div>
                    );
                })}
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
        slate: "border-neutral-100 bg-neutral-50/60 text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900/40 dark:text-neutral-300",
    }[tone];

    return (
        <div className={clsx("rounded-2xl border px-4 py-3 space-y-2", toneClass)}>
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em]">
                {icon}
                <span>{title}</span>
            </div>
            <p className="text-[13px] leading-relaxed font-medium text-neutral-700 dark:text-neutral-200">
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
                        <div className="text-[9px] font-black uppercase tracking-[0.16em] text-neutral-400 dark:text-neutral-500">
                            触发条件
                        </div>
                        <p className="text-[13px] leading-relaxed font-medium text-neutral-700 dark:text-neutral-200">
                            {compactSentence(trigger, 52)}
                        </p>
                    </div>
                )}
                {action && (
                    <div className="space-y-1">
                        <div className="text-[9px] font-black uppercase tracking-[0.16em] text-neutral-400 dark:text-neutral-500">
                            对应动作
                        </div>
                        <p className="text-[13px] leading-relaxed font-medium text-neutral-700 dark:text-neutral-200">
                            {compactSentence(action, 52)}
                        </p>
                    </div>
                )}
                {!trigger && !action && (
                    <p className="text-[13px] leading-relaxed font-medium text-neutral-700 dark:text-neutral-200">
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

    const t1 = aiData.target_price_1 && aiData.target_price_1 > entryHigh ? aiData.target_price_1 : null;
    const rawZones = [
        { name: isHolding ? "止损区" : "预设止损", start: axisMin, end: stopPrice, fill: "repeating-linear-gradient(45deg,#fecdd3,#fecdd3 4px,#fee2e2 4px,#fee2e2 8px)" },
        { name: "等待区", start: stopPrice, end: entryLow, fill: "#e2e8f0" },
        { name: "建仓区", start: entryLow, end: entryHigh, fill: "#10b981" },
        { name: "持有区", start: entryHigh, end: t1 ?? targetPrice, fill: "#e2e8f0" },
        { name: "止盈区", start: t1 ?? targetPrice, end: axisMax, fill: "repeating-linear-gradient(45deg,#bfdbfe,#bfdbfe 4px,#dbeafe 4px,#dbeafe 8px)" },
    ];

    const visibleZones = rawZones.filter(z => z.end > z.start);

    const keyPrices = [
        { val: stopPrice, label: "止损", color: "bg-rose-400 text-rose-600 dark:text-rose-400" },
        { val: entryLow, label: "建仓", color: "bg-emerald-400 text-emerald-600 dark:text-emerald-400" },
        { val: entryHigh, label: "加码", color: "bg-emerald-400 text-emerald-600 dark:text-emerald-400" },
        ...(t1 ? [{ val: t1, label: "T1", color: "bg-blue-400 text-blue-600 dark:text-blue-400" }] : []),
        { val: targetPrice, label: "目标", color: "bg-blue-400 text-blue-600 dark:text-blue-400" }
    ].filter((item, index, self) =>
        index === self.findIndex((t) => Math.abs(t.val - item.val) < 0.01)
    ).sort((a, b) => a.val - b.val);

    return (
        <div className="mb-7">
            <div className="relative h-5 mb-2">
                {visibleZones.map((zone, idx) => (
                    <div
                        key={`label-${idx}`}
                        className="absolute -translate-x-1/2 text-center"
                        style={{ left: `${getPos((zone.start + zone.end) / 2)}%` }}
                    >
                        <span className="text-[9px] font-black text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                            {zone.name}
                        </span>
                    </div>
                ))}
            </div>

            <div className="relative">
                <div
                    className="absolute z-20 flex flex-col items-center transition-all duration-500"
                    style={{ left: `${getPos(current)}%`, transform: "translateX(-50%)", top: "-32px" }}
                >
                    <div className="bg-neutral-900 dark:bg-black text-white text-[11px] font-black px-3 py-1.5 rounded-lg shadow-2xl border border-white/10 whitespace-nowrap">
                        当前 <span className="tabular-nums">${sanitizePrice(current)}</span>
                    </div>
                    <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-t-[6px] border-l-transparent border-r-transparent border-t-neutral-900 dark:border-t-black" />
                </div>

                <div
                    className="absolute z-10"
                    style={{ left: `${getPos(current)}%`, transform: "translateX(-50%)", top: "-4px" }}
                >
                    <div className="w-6 h-6 bg-blue-600 rounded-full border-[3px] border-white dark:border-zinc-950 shadow-lg ring-4 ring-blue-600/15" />
                </div>

                <div className="relative h-4 w-full bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden flex shadow-inner">
                    {visibleZones.map((zone, idx) => {
                        const width = `${((zone.end - zone.start) / totalRange) * 100}%`;
                        return (
                            <div
                                key={idx}
                                className="shrink-0 h-full"
                                style={{ width, background: zone.fill }}
                            />
                        );
                    })}
                </div>
            </div>

            <div className="relative h-6 mt-4">
                {keyPrices.map((tick, i) => (
                    <div
                        key={i}
                        className="absolute flex flex-col items-center -translate-x-1/2"
                        style={{ left: `${getPos(tick.val)}%` }}
                    >
                        <div className={clsx("w-px h-2 mb-1", tick.color.split(" ")[0])} />
                        <span className={clsx("text-[10px] font-bold tabular-nums", tick.color.split(" ").slice(1).join(" "))}>
                            {tick.val.toFixed(2)}
                            <span className="text-[8px] ml-0.5 opacity-70">{tick.label === "T1" ? "T1" : ""}</span>
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ========================================
// 交易执行详情 (Trade Execution Details)
// ========================================

function TradeExecutionDetails({
    aiData,
    currentPrice,
    stop,
    entryLow,
    entryHigh,
}: {
    aiData: NonNullable<AIVerdictProps["aiData"]>;
    currentPrice: number;
    stop: number;
    entryLow: number;
    entryHigh: number;
}) {
    const target = aiData.target_price;
    const rr = aiData.rr_ratio;
    const t1 = aiData.target_price_1;
    const t2 = aiData.target_price_2 ?? target;
    const maxPct = aiData.max_position_pct;
    const horizon = aiData.investment_horizon;
    const entryMid = (entryLow + entryHigh) / 2;

    const t1PctChange = t1 && entryMid ? ((t1 - entryMid) / entryMid * 100) : null;
    const t2PctChange = t2 && entryMid ? ((t2 - entryMid) / entryMid * 100) : null;
    const stopPctChange = stop && entryMid ? ((stop - entryMid) / entryMid * 100) : null;

    const horizonLabel = (() => {
        if (!horizon) return "波段";
        if (horizon.includes("周") || horizon.includes("week")) return "波段";
        if (horizon.includes("月") || horizon.includes("month")) return "中线";
        return "波段";
    })();

    return (
        <div className="mt-4 space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                <div className="bg-emerald-50 dark:bg-emerald-600/5 border border-emerald-100 dark:border-emerald-600/10 rounded-xl p-3">
                    <div className="text-[9px] font-black text-emerald-700 dark:text-emerald-400 uppercase mb-1">入场 Entry</div>
                    <div className="text-lg font-black text-emerald-600 dark:text-emerald-400 mono tabular-nums">
                        ${entryLow.toFixed(0)}–{entryHigh.toFixed(0)}
                    </div>
                    <p className="text-[9px] text-emerald-700 dark:text-emerald-400/80 mt-0.5">
                        {currentPrice > entryHigh ? "等待回踩" : "接近触发"}
                    </p>
                </div>

                <div className="bg-rose-50 dark:bg-rose-600/5 border border-rose-100 dark:border-rose-600/10 rounded-xl p-3">
                    <div className="text-[9px] font-black text-rose-700 dark:text-rose-400 uppercase mb-1">止损 Stop</div>
                    <div className="text-lg font-black text-rose-600 dark:text-rose-400 mono tabular-nums">
                        ${stop.toFixed(2)}
                    </div>
                    {stopPctChange != null && (
                        <p className="text-[9px] text-rose-700 dark:text-rose-400/80 mt-0.5">
                            {stopPctChange.toFixed(1)}% · 前低下方
                        </p>
                    )}
                </div>

                <div className="bg-blue-50 dark:bg-blue-600/5 border border-blue-100 dark:border-blue-600/10 rounded-xl p-3">
                    <div className="text-[9px] font-black text-blue-700 dark:text-blue-400 uppercase mb-1">T1 减仓 1/3</div>
                    <div className="text-lg font-black text-blue-600 dark:text-blue-400 mono tabular-nums">
                        ${t1?.toFixed(2) ?? target?.toFixed(2) ?? "--"}
                    </div>
                    {t1PctChange != null && (
                        <p className="text-[9px] text-blue-700 dark:text-blue-400/80 mt-0.5">
                            +{t1PctChange.toFixed(1)}% · 锁利润
                        </p>
                    )}
                </div>

                <div className="bg-blue-50 dark:bg-blue-600/5 border border-blue-100 dark:border-blue-600/10 rounded-xl p-3">
                    <div className="text-[9px] font-black text-blue-700 dark:text-blue-400 uppercase mb-1">T2 止盈清仓</div>
                    <div className="text-lg font-black text-blue-600 dark:text-blue-400 mono tabular-nums">
                        ${t2?.toFixed(2) ?? "--"}
                    </div>
                    {t2PctChange != null && (
                        <p className="text-[9px] text-blue-700 dark:text-blue-400/80 mt-0.5">
                            +{t2PctChange.toFixed(1)}% · 完整兑现
                        </p>
                    )}
                </div>

                <div className="bg-neutral-50 dark:bg-zinc-800/50 border border-neutral-100 dark:border-zinc-800 rounded-xl p-3">
                    <div className="text-[9px] font-black text-neutral-600 dark:text-neutral-400 uppercase mb-1">仓位 Size</div>
                    <div className="text-lg font-black text-neutral-700 dark:text-neutral-200 mono tabular-nums">
                        {maxPct != null ? `${(maxPct * 0.7).toFixed(1)}→${maxPct.toFixed(1)}%` : "--"}
                    </div>
                    <p className="text-[9px] text-neutral-500 dark:text-neutral-500 mt-0.5">{horizonLabel} · 分 2 笔</p>
                </div>
            </div>

        </div>
    );
}

// ========================================
// 信号追踪与复盘 (Truth Tracker)
// ========================================

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

function TruthTracker({
    analysisHistory,
    selectedItem
}: {
    analysisHistory: AIVerdictProps["analysisHistory"];
    selectedItem: AIVerdictProps["selectedItem"];
}) {
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
                    <div className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-3 border-b border-neutral-100 pb-2 dark:border-zinc-800 text-[8px] font-bold uppercase tracking-wider text-neutral-400">
                        <span>日期</span>
                        <span>动作</span>
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
                                className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-3 border-b border-neutral-50 py-2.5 last:border-0 dark:border-zinc-800/50"
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
}
