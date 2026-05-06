"use client";

import React from "react";
import clsx from "clsx";
import { AlertTriangle } from "lucide-react";

interface SectorRow {
    sector: string;
    weight: number;
    value: number;
}

interface ImpactData {
    current_sector_exposure: SectorRow[];
    projected_sector_exposure: SectorRow[];
    current_beta: number;
    projected_beta: number;
    current_sharpe: number;
    projected_sharpe: number;
    max_recommended_pct: number;
    ai_suggestion: string;
    warnings: string[];
}

interface PortfolioLinkageProps {
    ticker: string;
    positionPct: number;
    impactData: ImpactData | null;
    isLoading?: boolean;
}

export function PortfolioLinkage({ ticker, positionPct, impactData, isLoading }: PortfolioLinkageProps) {
    if (isLoading) {
        return (
            <div className="rounded-2xl border overflow-hidden" style={{ background: "linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)", borderColor: "#1e3a5f" }}>
                <div className="px-6 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
                    <span className="text-[11px] font-black text-slate-300 uppercase tracking-wider">组合联动视角</span>
                </div>
                <div className="p-6 flex items-center justify-center text-slate-400 text-sm">
                    计算中...
                </div>
            </div>
        );
    }

    if (!impactData) return null;

    const {
        current_sector_exposure: currentSectors,
        projected_sector_exposure: projectedSectors,
        current_beta,
        projected_beta,
        current_sharpe,
        projected_sharpe,
        max_recommended_pct,
        ai_suggestion,
        warnings,
    } = impactData;

    const SECTOR_COLORS: Record<string, { current: string; projected: string }> = {
        Technology: { current: "bg-blue-500/40", projected: "bg-amber-500" },
        Healthcare: { current: "bg-emerald-500/40", projected: "bg-emerald-500" },
        Financials: { current: "bg-violet-500/40", projected: "bg-violet-500" },
        Industrials: { current: "bg-teal-500/40", projected: "bg-teal-500" },
        Consumer: { current: "bg-pink-500/40", projected: "bg-pink-500" },
        Energy: { current: "bg-orange-500/40", projected: "bg-orange-500" },
    };

    return (
        <div className="rounded-2xl border overflow-hidden" style={{ background: "linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)", borderColor: "#1e3a5f" }}>
            {/* Header */}
            <div className="px-6 py-3 border-b flex items-center gap-2" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
                <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="text-[11px] font-black text-slate-300 uppercase tracking-wider">组合联动视角</span>
                <span className="text-[10px] text-slate-500">— 加仓 {ticker} {positionPct}% 对组合意味着什么</span>
            </div>

            <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Left: Sector Exposure Changes */}
                    <div>
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-3">
                            加仓后行业敞口变化
                        </div>
                        <div className="space-y-2.5">
                            {currentSectors.map((sector) => {
                                const projected = projectedSectors.find(s => s.sector === sector.sector);
                                const projectedWeight = projected?.weight ?? sector.weight;
                                const colorSet = SECTOR_COLORS[sector.sector] ?? { current: "bg-slate-500/40", projected: "bg-slate-500" };
                                const isOverLimit = projectedWeight > 40;

                                return (
                                    <div key={sector.sector}>
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-[10px] text-slate-300 font-medium">{sector.sector}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] text-slate-500 mono">{sector.weight.toFixed(1)}%</span>
                                                <span className={clsx("text-[10px] font-black mono", isOverLimit ? "text-amber-400" : "text-slate-300")}>
                                                    → {projectedWeight.toFixed(1)}%
                                                </span>
                                            </div>
                                        </div>
                                        <div className="h-2 bg-slate-700 rounded-full overflow-hidden relative">
                                            <div className={clsx("h-full rounded-full absolute", colorSet.current)} style={{ width: `${sector.weight}%` }} />
                                            <div className={clsx("h-full rounded-full", colorSet.projected)} style={{ width: `${projectedWeight}%`, opacity: 0.7 }} />
                                            {/* 40% warning line */}
                                            <div className="absolute top-0 bottom-0 w-0.5 bg-rose-400" style={{ left: "40%" }} />
                                        </div>
                                        {isOverLimit && (
                                            <div className="flex items-center gap-1 mt-1">
                                                <span className="text-[9px] text-rose-400 font-bold">⚠ 超过建议上限 40%，行业集中度偏高</span>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Right: Key Metrics */}
                    <div>
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-3">
                            组合关键指标影响
                        </div>
                        <div className="space-y-3">
                            {/* Beta */}
                            <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                                <span className="text-[11px] text-slate-400">组合 Beta</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-slate-500 line-through mono">{current_beta.toFixed(2)}</span>
                                    <span className="text-sm font-black text-white mono">{projected_beta.toFixed(2)}</span>
                                    <span className={clsx(
                                        "text-[9px] font-black px-1.5 py-0.5 rounded border",
                                        projected_beta > current_beta
                                            ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                                            : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                    )}>
                                        {projected_beta > current_beta ? "↑ 波动" : "↓ 稳健"}
                                    </span>
                                </div>
                            </div>

                            {/* Sharpe */}
                            <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                                <span className="text-[11px] text-slate-400">Sharpe 预期</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-slate-500 line-through mono">{current_sharpe.toFixed(2)}</span>
                                    <span className="text-sm font-black text-emerald-400 mono">{projected_sharpe.toFixed(2)}</span>
                                    <span className="text-[9px] font-black px-1.5 py-0.5 rounded border bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                                        ↑ 改善
                                    </span>
                                </div>
                            </div>

                            {/* Max Position */}
                            <div className="flex items-center justify-between py-2">
                                <span className="text-[11px] text-slate-400">建议最大仓位</span>
                                <span className="text-sm font-black text-blue-400 mono">
                                    {positionPct}% → {max_recommended_pct}%
                                </span>
                            </div>
                        </div>

                        {/* AI Suggestion */}
                        {ai_suggestion && (
                            <div className="mt-3 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3">
                                <p className="text-[10px] text-rose-300 leading-relaxed">
                                    <span className="font-black">AI 建议：</span>{ai_suggestion}
                                </p>
                            </div>
                        )}

                        {/* Warnings */}
                        {warnings.length > 0 && (
                            <div className="mt-2 space-y-1">
                                {warnings.map((w, i) => (
                                    <div key={i} className="flex items-center gap-1.5 text-[10px] text-amber-300">
                                        <AlertTriangle className="h-3 w-3" />
                                        <span>{w}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
