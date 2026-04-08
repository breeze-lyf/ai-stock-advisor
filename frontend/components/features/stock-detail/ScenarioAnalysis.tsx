"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Target, Clock, BarChart3 } from "lucide-react";
import { ScenarioAnalysisData } from "@/features/analysis/hooks/useEnhancedAnalysis";

interface ScenarioAnalysisProps {
    ticker: string;
    scenarioAnalysis?: {
        bull_case: {
            target_price: number;
            upside_percent: number;
            probability: number;
            timeframe: string;
            key_drivers: string[];
            description?: string;
        };
        base_case: {
            target_price: number;
            upside_percent: number;
            probability: number;
            timeframe: string;
            key_drivers: string[];
            description?: string;
        };
        bear_case: {
            target_price: number;
            downside_percent: number;
            probability: number;
            timeframe: string;
            risk_factors: string[];
            description?: string;
        };
    } | null;
    loading?: boolean;
}

export function ScenarioAnalysis({
    ticker,
    scenarioAnalysis,
    loading = false,
}: ScenarioAnalysisProps) {
    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
                <span className="ml-3 text-slate-500">生成情景分析中...</span>
            </div>
        );
    }

    if (!scenarioAnalysis) {
        return (
            <div className="py-8 text-center text-slate-400">
                <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">暂无情景分析数据</p>
            </div>
        );
    }

    const scenarios = [
        {
            title: "乐观情景",
            color: "emerald",
            icon: TrendingUp,
            data: scenarioAnalysis.bull_case,
        },
        {
            title: "基准情景",
            color: "blue",
            icon: Minus,
            data: scenarioAnalysis.base_case,
        },
        {
            title: "悲观情景",
            color: "red",
            icon: TrendingDown,
            data: scenarioAnalysis.bear_case,
        },
    ];

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3 mb-6">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">情景分析</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {scenarios.map(({ title, color, icon: Icon, data }) => (
                    <div
                        key={title}
                        className={`p-4 rounded-lg border ${
                            color === "emerald"
                                ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800"
                                : color === "red"
                                ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                                : "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
                        }`}
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <Icon className={`h-4 w-4 ${color === "emerald" ? "text-emerald-600" : color === "red" ? "text-red-600" : "text-blue-600"}`} />
                            <span className={`font-medium text-sm ${color === "emerald" ? "text-emerald-700 dark:text-emerald-300" : color === "red" ? "text-red-700 dark:text-red-300" : "text-blue-700 dark:text-blue-300"}`}>
                                {title}
                            </span>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-500">目标价</span>
                                <span className="font-semibold text-slate-900 dark:text-white">
                                    ${data.target_price?.toFixed(2)}
                                </span>
                            </div>
                            {"upside_percent" in data && data.upside_percent !== undefined && (
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-500">上涨空间</span>
                                    <span className="font-semibold text-emerald-600">
                                        +{data.upside_percent.toFixed(2)}%
                                    </span>
                                </div>
                            )}
                            {"downside_percent" in data && data.downside_percent !== undefined && (
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-500">下跌空间</span>
                                    <span className="font-semibold text-red-600">
                                        {data.downside_percent.toFixed(2)}%
                                    </span>
                                </div>
                            )}
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-500">概率</span>
                                <span className="font-semibold text-slate-900 dark:text-white">
                                    {data.probability * 100}%
                                </span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-500">时间框架</span>
                                <span className="font-semibold text-slate-900 dark:text-white">
                                    {data.timeframe}
                                </span>
                            </div>
                        </div>

                        {"key_drivers" in data && data.key_drivers && data.key_drivers.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                                <div className="text-xs text-slate-500 mb-2">驱动因素</div>
                                <ul className="space-y-1">
                                    {data.key_drivers.map((driver, idx) => (
                                        <li key={idx} className="text-xs text-slate-600 dark:text-slate-400 flex items-start gap-1">
                                            <span className="text-emerald-500 mt-0.5">•</span>
                                            {driver}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {"risk_factors" in data && data.risk_factors && data.risk_factors.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                                <div className="text-xs text-slate-500 mb-2">风险因素</div>
                                <ul className="space-y-1">
                                    {data.risk_factors.map((factor, idx) => (
                                        <li key={idx} className="text-xs text-red-600 dark:text-red-400 flex items-start gap-1">
                                            <span className="text-red-500 mt-0.5">•</span>
                                            {factor}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
