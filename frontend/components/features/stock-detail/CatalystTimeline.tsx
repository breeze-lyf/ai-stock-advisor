"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Calendar, Zap } from "lucide-react";

interface Catalyst {
    date: string;
    event: string;
    type: string;
    impact: string;
    description: string;
}

interface CatalystTimelineProps {
    catalysts?: Catalyst[];
}

const TYPE_LABELS: Record<string, string> = {
    earnings: "财报",
    fomc: "FOMC",
    product: "产品",
    macro: "宏观",
    technical: "技术",
};

const TYPE_COLORS: Record<string, string> = {
    earnings: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800",
    fomc: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800",
    product: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800",
    macro: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700",
    technical: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-200 dark:border-cyan-800",
};

const IMPACT_CONFIG = {
    bullish: {
        icon: TrendingUp,
        color: "text-emerald-500",
        dotColor: "bg-emerald-500",
        lineColor: "border-emerald-200 dark:border-emerald-900",
    },
    bearish: {
        icon: TrendingDown,
        color: "text-red-500",
        dotColor: "bg-red-500",
        lineColor: "border-red-200 dark:border-red-900",
    },
    neutral: {
        icon: Minus,
        color: "text-slate-400",
        dotColor: "bg-slate-400",
        lineColor: "border-slate-200 dark:border-slate-700",
    },
};

function formatDate(dateStr: string): string {
    if (dateStr === "未知" || !dateStr) return "待定";
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
    } catch {
        return dateStr;
    }
}

function getDaysAway(dateStr: string): string | null {
    if (dateStr === "未知" || !dateStr) return null;
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return null;
        const diff = Math.ceil((d.getTime() - Date.now()) / 86400000);
        if (diff < 0) return "已过";
        if (diff === 0) return "今日";
        return `${diff}天后`;
    } catch {
        return null;
    }
}

export function CatalystTimeline({ catalysts }: CatalystTimelineProps) {
    if (!catalysts || catalysts.length === 0) return null;

    // Sort by date ascending, unknowns last
    const sorted = [...catalysts].sort((a, b) => {
        if (a.date === "未知") return 1;
        if (b.date === "未知") return -1;
        return new Date(a.date).getTime() - new Date(b.date).getTime();
    });

    return (
        <div className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-2xl p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5 text-slate-400" strokeWidth={2.5} />
                <h3 className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                    催化剂时间轴
                </h3>
            </div>

            {/* Timeline */}
            <div className="relative pl-5">
                {/* Vertical line */}
                <div className="absolute left-[7px] top-2 bottom-2 w-px bg-slate-100 dark:bg-zinc-800" />

                <div className="space-y-3">
                    {sorted.map((catalyst, idx) => {
                        const impact = IMPACT_CONFIG[catalyst.impact as keyof typeof IMPACT_CONFIG] ?? IMPACT_CONFIG.neutral;
                        const ImpactIcon = impact.icon;
                        const daysAway = getDaysAway(catalyst.date);
                        const typeLabel = TYPE_LABELS[catalyst.type] ?? catalyst.type;
                        const typeColor = TYPE_COLORS[catalyst.type] ?? TYPE_COLORS.macro;

                        return (
                            <div key={idx} className="relative flex items-start gap-3">
                                {/* Timeline dot */}
                                <div className={`absolute -left-5 mt-1.5 w-3 h-3 rounded-full border-2 border-white dark:border-zinc-900 ${impact.dotColor} flex-shrink-0`} />

                                {/* Content */}
                                <div className="flex-1 min-w-0 space-y-1">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {/* Date badge */}
                                        <span className="text-[10px] font-black text-slate-500 dark:text-slate-400 tabular-nums">
                                            {formatDate(catalyst.date)}
                                        </span>

                                        {/* Days away */}
                                        {daysAway && (
                                            <span className="text-[9px] font-semibold text-slate-400 dark:text-slate-500">
                                                ({daysAway})
                                            </span>
                                        )}

                                        {/* Type tag */}
                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${typeColor}`}>
                                            {typeLabel}
                                        </span>

                                        {/* Impact icon */}
                                        <ImpactIcon className={`h-3 w-3 ${impact.color}`} strokeWidth={2.5} />
                                    </div>

                                    {/* Event name */}
                                    <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200 leading-snug">
                                        {catalyst.event}
                                    </p>

                                    {/* Description */}
                                    <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-snug">
                                        {catalyst.description}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Empty hint */}
            {sorted.length === 0 && (
                <div className="flex items-center gap-2 text-slate-300 dark:text-slate-600 py-2">
                    <Zap className="h-4 w-4" />
                    <span className="text-xs">暂无已识别催化剂</span>
                </div>
            )}
        </div>
    );
}
