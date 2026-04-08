"use client";

import React from "react";
import { Clock, TrendingUp, TrendingDown, Minus, Activity, Target } from "lucide-react";

interface TimeframeData {
    timeframe: string;
    trend: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    key_levels: number[];
    strategy: string;
    reference_ma?: string;
}

interface MultiTimeframeAnalysisData {
    short_term: TimeframeData;
    medium_term: TimeframeData;
    long_term: TimeframeData;
}

interface MultiTimeframeAnalysisProps {
    ticker: string;
    currentPrice?: number;
    analysis?: MultiTimeframeAnalysisData | null;
    loading?: boolean;
}

export function MultiTimeframeAnalysis({
    ticker,
    currentPrice,
    analysis,
    loading = false,
}: MultiTimeframeAnalysisProps) {
    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                <span className="ml-3 text-slate-500">生成多时间框架分析中...</span>
            </div>
        );
    }

    if (!analysis || "error" in analysis) {
        return (
            <div className="py-8 text-center text-slate-400">
                <Clock className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">暂无多时间框架分析数据</p>
            </div>
        );
    }

    const getTrendConfig = (trend: string) => {
        switch (trend) {
            case "BULLISH":
                return {
                    icon: TrendingUp,
                    color: "text-emerald-600 dark:text-emerald-400",
                    bgColor: "bg-emerald-100 dark:bg-emerald-900/20",
                    label: "看涨",
                };
            case "BEARISH":
                return {
                    icon: TrendingDown,
                    color: "text-red-600 dark:text-red-400",
                    bgColor: "bg-red-100 dark:bg-red-900/20",
                    label: "看跌",
                };
            default:
                return {
                    icon: Minus,
                    color: "text-slate-600 dark:text-slate-400",
                    bgColor: "bg-slate-100 dark:bg-slate-800",
                    label: "中性",
                };
        }
    };

    const timeframes = [
        {
            title: "短线",
            subtitle: "Short Term",
            period: "1-5 日",
            data: analysis.short_term,
        },
        {
            title: "中线",
            subtitle: "Medium Term",
            period: "1-4 周",
            data: analysis.medium_term,
        },
        {
            title: "长线",
            subtitle: "Long Term",
            period: "3-12 月",
            data: analysis.long_term,
        },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
                <Clock className="h-5 w-5 text-slate-400" />
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    多时间框架分析
                </h3>
            </div>

            <div className="grid gap-4">
                {timeframes.map((tf) => {
                    const TrendIcon = getTrendConfig(tf.data.trend).icon;
                    const trendColor = getTrendConfig(tf.data.trend).color;
                    const trendBgColor = getTrendConfig(tf.data.trend).bgColor;

                    return (
                        <div
                            key={tf.title}
                            className="rounded-xl p-4 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                        >
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg ${trendBgColor}`}>
                                        <TrendIcon className={`h-5 w-5 ${trendColor}`} />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                                                {tf.title}
                                            </h4>
                                            <span className={`text-xs font-bold px-2 py-0.5 rounded ${trendBgColor} ${trendColor}`}>
                                                {getTrendConfig(tf.data.trend).label}
                                            </span>
                                        </div>
                                        <p className="text-[10px] text-slate-500">
                                            {tf.subtitle} · {tf.period}
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-xs text-slate-500 mb-1">置信度</div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-20 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full ${trendColor.replace("text-", "bg-")}`}
                                                style={{ width: `${tf.data.confidence * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                                            {(tf.data.confidence * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="grid md:grid-cols-3 gap-4">
                                {/* 关键价位 */}
                                <div className="md:col-span-1">
                                    <div className="flex items-center gap-1.5 mb-2">
                                        <Target className="h-3 w-3 text-slate-400" />
                                        <span className="text-[10px] text-slate-500 uppercase">关键价位</span>
                                    </div>
                                    <div className="space-y-1">
                                        {tf.data.key_levels.map((level: number, i: number) => (
                                            <div key={i} className="flex items-center justify-between text-xs">
                                                <span className="text-slate-500">
                                                    {i === 0 ? "支撑" : i === 1 ? "当前" : "阻力"}
                                                </span>
                                                <span className="font-bold text-slate-700 dark:text-slate-300">
                                                    ${level.toFixed(2)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* 参考均线 */}
                                {tf.data.reference_ma && (
                                    <div className="md:col-span-1">
                                        <div className="flex items-center gap-1.5 mb-2">
                                            <Activity className="h-3 w-3 text-slate-400" />
                                            <span className="text-[10px] text-slate-500 uppercase">参考均线</span>
                                        </div>
                                        <p className="text-xs text-slate-600 dark:text-slate-400">
                                            {tf.data.reference_ma}
                                        </p>
                                    </div>
                                )}

                                {/* 策略建议 */}
                                <div className="md:col-span-1">
                                    <div className="flex items-center gap-1.5 mb-2">
                                        <TrendIcon className="h-3 w-3 text-slate-400" />
                                        <span className="text-[10px] text-slate-500 uppercase">策略建议</span>
                                    </div>
                                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                        {tf.data.strategy}
                                    </p>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* 当前股价参考 */}
            {currentPrice && (
                <div className="mt-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 flex items-center justify-between">
                    <span className="text-xs text-slate-500">当前股价</span>
                    <span className="text-lg font-black text-slate-900 dark:text-slate-100">
                        ${currentPrice.toFixed(2)}
                    </span>
                </div>
            )}
        </div>
    );
}
