"use client";

import { useState } from "react";

interface Assumption {
    assumption: string;
    breakpoint: string;
    risk_level?: string;
    metric_label?: string;
    metric_value?: string;
}

interface KeyAssumptionsProps {
    assumptions?: Assumption[];
}

const RISK_CONFIG = {
    high: {
        dotColor: "bg-rose-100 border-rose-200 text-rose-600",
        tagBg: "bg-rose-50 dark:bg-rose-600/10",
        tagColor: "text-rose-600 dark:text-rose-400",
        tagBorder: "border-rose-200 dark:border-rose-600/20",
        metricColor: "text-rose-600 dark:text-rose-400",
        rowHover: "hover:bg-rose-50/40 dark:hover:bg-rose-600/10",
        rowOpen: "bg-rose-50/25 dark:bg-rose-600/5",
        pulse: true,
        label: "核心假设",
    },
    medium: {
        dotColor: "bg-amber-100 border-amber-200 text-amber-600",
        tagBg: "bg-amber-50 dark:bg-amber-600/10",
        tagColor: "text-amber-600 dark:text-amber-400",
        tagBorder: "border-amber-200 dark:border-amber-600/20",
        metricColor: "text-amber-600 dark:text-amber-400",
        rowHover: "hover:bg-amber-50/30 dark:hover:bg-amber-600/10",
        rowOpen: "bg-amber-50/20 dark:bg-amber-600/5",
        pulse: false,
        label: "辅助假设",
    },
    low: {
        dotColor: "bg-emerald-100 border-emerald-200 text-emerald-600",
        tagBg: "bg-emerald-50 dark:bg-emerald-600/10",
        tagColor: "text-emerald-600 dark:text-emerald-400",
        tagBorder: "border-emerald-200 dark:border-emerald-600/20",
        metricColor: "text-emerald-600 dark:text-emerald-400",
        rowHover: "hover:bg-emerald-50/30 dark:hover:bg-emerald-600/10",
        rowOpen: "bg-emerald-50/20 dark:bg-emerald-600/5",
        pulse: false,
        label: "基本面假设",
    },
} as const;

export function KeyAssumptions({ assumptions }: KeyAssumptionsProps) {
    const [expanded, setExpanded] = useState<number | null>(null);

    if (!assumptions || assumptions.length === 0) return null;

    return (
        <div className="bg-white dark:bg-zinc-900 border border-neutral-100 dark:border-zinc-800 rounded-[2rem] px-4 md:px-10 py-6 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-3 border-b border-neutral-100 dark:border-zinc-800 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                <h3 className="text-[11px] font-black text-neutral-700 dark:text-neutral-300 uppercase tracking-wider">
                    关键假设断点
                </h3>
                <span className="text-[10px] text-neutral-400">— 任意一项失效，策略逻辑瓦解</span>
                <span className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded-md bg-orange-50 dark:bg-orange-600/10 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-600/20">
                    ⚠ 需持续监控
                </span>
            </div>

            {/* Assumption list */}
            <div className="divide-y divide-neutral-50 dark:divide-zinc-800">
                {assumptions.map((item, idx) => {
                    const isOpen = expanded === idx;
                    const riskLevel = item.risk_level as keyof typeof RISK_CONFIG | undefined;
                    const risk = riskLevel && RISK_CONFIG[riskLevel] ? RISK_CONFIG[riskLevel] : RISK_CONFIG.medium;

                    return (
                        <div
                            key={idx}
                            className={`px-6 py-4 flex items-start gap-4 cursor-pointer transition-colors ${risk.pulse ? "assumption-pulse" : ""} ${risk.rowHover} ${isOpen ? risk.rowOpen : ""}`}
                            onClick={() => setExpanded(isOpen ? null : idx)}
                        >
                            {/* Number dot */}
                            <div className={`flex-shrink-0 mt-0.5 w-6 h-6 rounded-full flex items-center justify-center border ${risk.dotColor}`}>
                                <span className="text-[10px] font-black">{idx + 1}</span>
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap mb-1">
                                    <span className="font-bold text-sm text-neutral-900 dark:text-neutral-200">
                                        {item.assumption}
                                    </span>
                                    <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${risk.tagBg} ${risk.tagColor} ${risk.tagBorder}`}>
                                        {risk.label}
                                    </span>
                                </div>
                                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 leading-relaxed">
                                    {item.breakpoint}
                                </p>
                                {isOpen && (
                                    <div className="mt-2 text-[10px] text-neutral-400 dark:text-neutral-500">
                                        点击卡片可切换查看状态，建议持续关注这一假设是否被市场数据证伪。
                                    </div>
                                )}
                            </div>

                            {/* Right metric column */}
                            {item.metric_label && item.metric_value && (
                                <div className="flex-shrink-0 text-right">
                                    <div className="text-[10px] text-neutral-400">{item.metric_label}</div>
                                    <div className={`text-lg font-black mono ${risk.metricColor}`}>
                                        {item.metric_value}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
