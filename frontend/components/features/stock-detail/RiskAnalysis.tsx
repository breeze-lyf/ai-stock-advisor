"use client";

import React from "react";
import { Shield, ShieldAlert, ShieldCheck, TrendingUp, Activity, AlertTriangle } from "lucide-react";
import { RiskAnalysisData } from "@/features/analysis/hooks/useEnhancedAnalysis";

interface RiskAnalysisProps {
    ticker: string;
    riskAnalysis?: RiskAnalysisData | null;
    loading?: boolean;
}

export function RiskAnalysis({ ticker, riskAnalysis, loading = false }: RiskAnalysisProps) {
    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
                <span className="ml-3 text-slate-500">生成风险分析中...</span>
            </div>
        );
    }

    if (!riskAnalysis) {
        return (
            <div className="py-8 text-center text-slate-400">
                <Shield className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">暂无风险分析数据</p>
            </div>
        );
    }

    const getRiskIcon = (score: number) => {
        if (score >= 7) return ShieldAlert;
        if (score >= 4) return Shield;
        return ShieldCheck;
    };

    const getRiskColor = (score: number) => {
        if (score >= 7) return "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/20";
        if (score >= 4) return "text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/20";
        return "text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/20";
    };

    const getRiskLabel = (score: number) => {
        if (score >= 7) return "高风险";
        if (score >= 4) return "中风险";
        return "低风险";
    };

    const getRiskBadgeColor = (score: number) => {
        if (score >= 7) return "bg-red-500";
        if (score >= 4) return "bg-amber-500";
        return "bg-emerald-500";
    };

    const risks = [
        {
            title: "市场风险",
            subtitle: "Market Risk",
            score: riskAnalysis.market_risk?.score || 0,
            factors: riskAnalysis.market_risk?.factors || [],
            icon: TrendingUp,
        },
        {
            title: "技术面风险",
            subtitle: "Technical Risk",
            score: riskAnalysis.technical_risk?.score || 0,
            factors: riskAnalysis.technical_risk?.factors || [],
            icon: Activity,
        },
        {
            title: "行业风险",
            subtitle: "Sector Risk",
            score: riskAnalysis.sector_risk?.score || 0,
            factors: riskAnalysis.sector_risk?.factors || [],
            icon: Shield,
        },
        {
            title: "公司风险",
            subtitle: "Company Risk",
            score: riskAnalysis.company_risk?.score || 0,
            factors: riskAnalysis.company_risk?.factors || [],
            icon: AlertTriangle,
        },
    ];

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3 mb-6">
                <Shield className="h-5 w-5 text-amber-500" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">风险分析</h3>
                <div className="ml-auto flex items-center gap-2">
                    <span className="text-xs text-slate-500">综合评分</span>
                    <div className="flex items-center gap-1">
                        <div className="w-20 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                                className={`h-full ${getRiskBadgeColor(riskAnalysis.overall_risk_score)}`}
                                style={{ width: `${(riskAnalysis.overall_risk_score / 10) * 100}%` }}
                            />
                        </div>
                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300">
                            {riskAnalysis.overall_risk_score.toFixed(1)}/10
                        </span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {risks.map((risk) => {
                    const Icon = risk.icon;
                    const score = risk.score;

                    return (
                        <div
                            key={risk.title}
                            className="rounded-xl p-4 border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50"
                        >
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                                        {risk.title}
                                    </h4>
                                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">
                                        {risk.subtitle}
                                    </p>
                                </div>
                                <div className={`p-2 rounded-lg ${getRiskColor(score)}`}>
                                    <Icon className="h-4 w-4" />
                                </div>
                            </div>

                            <div className="flex items-center justify-between mb-3">
                                <span className={`text-xs font-bold px-2 py-1 rounded-full ${getRiskColor(score)}`}>
                                    {getRiskLabel(score)}
                                </span>
                                <span className="text-xs text-slate-500">
                                    评分：{score}/10
                                </span>
                            </div>

                            {risk.factors.length > 0 && (
                                <ul className="space-y-1">
                                    {risk.factors.map((factor, idx) => (
                                        <li key={idx} className="text-xs text-slate-600 dark:text-slate-400 flex items-start gap-1">
                                            <span className="text-amber-500 mt-0.5">•</span>
                                            {factor}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* 技术指标 */}
            <div className="grid grid-cols-3 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
                {riskAnalysis.beta && (
                    <div className="text-center">
                        <div className="text-xs text-slate-500 mb-1">β系数</div>
                        <div className="text-lg font-bold text-slate-900 dark:text-white">
                            {riskAnalysis.beta.toFixed(2)}
                        </div>
                    </div>
                )}
                {riskAnalysis.rsi && (
                    <div className="text-center">
                        <div className="text-xs text-slate-500 mb-1">RSI(14)</div>
                        <div className={`text-lg font-bold ${
                            riskAnalysis.rsi > 70 ? "text-red-600" : riskAnalysis.rsi < 30 ? "text-emerald-600" : "text-slate-900 dark:text-white"
                        }`}>
                            {riskAnalysis.rsi.toFixed(1)}
                        </div>
                    </div>
                )}
                {riskAnalysis.volatility && (
                    <div className="text-center">
                        <div className="text-xs text-slate-500 mb-1">波动率</div>
                        <div className="text-lg font-bold text-slate-900 dark:text-white">
                            {(riskAnalysis.volatility * 100).toFixed(1)}%
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
