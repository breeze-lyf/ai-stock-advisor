"use client";

import React from "react";

interface ConfidenceBreakdownProps {
    confidenceLevel?: number;
    breakdown?: {
        technical?: number;
        fundamental?: number;
        macro?: number;
        sentiment?: number;
    };
}

const DIMENSIONS = [
    { key: "technical" as const, label: "技术面", color: "bg-blue-500" },
    { key: "fundamental" as const, label: "基本面", color: "bg-emerald-500" },
    { key: "macro" as const, label: "宏观面", color: "bg-amber-500" },
    { key: "sentiment" as const, label: "情绪面", color: "bg-purple-500" },
];

function getConfidenceColor(score: number): string {
    if (score >= 75) return "text-emerald-500";
    if (score >= 50) return "text-amber-500";
    return "text-red-500";
}

function getConfidenceBgColor(score: number): string {
    if (score >= 75) return "bg-emerald-500";
    if (score >= 50) return "bg-amber-500";
    return "bg-red-500";
}

export function ConfidenceBreakdown({ confidenceLevel, breakdown }: ConfidenceBreakdownProps) {
    if (!confidenceLevel && !breakdown) return null;

    const overall = confidenceLevel ?? 0;

    return (
        <div className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-2xl p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                    信心构成
                </h3>
                {confidenceLevel !== undefined && (
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 dark:text-slate-500">综合置信度</span>
                        <span className={`text-lg font-black tabular-nums ${getConfidenceColor(overall)}`}>
                            {overall}
                        </span>
                    </div>
                )}
            </div>

            {/* Overall bar */}
            {confidenceLevel !== undefined && (
                <div className="space-y-1">
                    <div className="w-full bg-slate-100 dark:bg-zinc-800 rounded-full h-2 overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-700 ${getConfidenceBgColor(overall)}`}
                            style={{ width: `${Math.min(overall, 100)}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Dimension breakdown */}
            {breakdown && (
                <div className="grid grid-cols-2 gap-2 pt-1">
                    {DIMENSIONS.map(({ key, label, color }) => {
                        const val = breakdown[key];
                        if (val === undefined) return null;
                        return (
                            <div key={key} className="space-y-1.5">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">
                                        {label}
                                    </span>
                                    <span className={`text-[10px] font-black tabular-nums ${getConfidenceColor(val)}`}>
                                        {val}
                                    </span>
                                </div>
                                <div className="w-full bg-slate-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-700 ${color}`}
                                        style={{ width: `${Math.min(val, 100)}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
