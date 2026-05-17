"use client";

import React from "react";
import clsx from "clsx";
import { AlertTriangle, Users } from "lucide-react";

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

const SECTOR_LABELS: Record<string, string> = {
    Technology: "科技",
    Healthcare: "医疗",
    Financials: "金融",
    Industrials: "工业",
    Consumer: "消费",
    Energy: "能源",
    Utilities: "公用事业",
    Unknown: "未知",
};

const SECTOR_COLORS: Record<string, { current: string; projected: string; text: string }> = {
    Technology: { current: "bg-slate-400", projected: "bg-amber-400", text: "text-amber-400" },
    Healthcare: { current: "bg-slate-400", projected: "bg-emerald-400", text: "text-emerald-400" },
    Financials: { current: "bg-slate-400", projected: "bg-violet-400", text: "text-violet-400" },
    Industrials: { current: "bg-slate-400", projected: "bg-cyan-400", text: "text-cyan-400" },
    Consumer: { current: "bg-slate-400", projected: "bg-pink-400", text: "text-pink-400" },
    Energy: { current: "bg-slate-400", projected: "bg-orange-400", text: "text-orange-400" },
    Utilities: { current: "bg-slate-400", projected: "bg-sky-400", text: "text-sky-400" },
    Unknown: { current: "bg-slate-400", projected: "bg-slate-200", text: "text-slate-200" },
};

function formatDelta(current: number, projected: number): string {
    const diff = projected - current;
    return `${diff >= 0 ? "+" : ""}${diff.toFixed(1)}`;
}

function buildRows(impactData: ImpactData) {
    return impactData.projected_sector_exposure.map((projected) => {
        const current = impactData.current_sector_exposure.find((item) => item.sector === projected.sector);
        return {
            sector: projected.sector,
            currentWeight: current?.weight ?? 0,
            projectedWeight: projected.weight,
            isOverLimit: projected.weight > 40,
        };
    });
}

export function PortfolioLinkage({ ticker, positionPct, impactData, isLoading }: PortfolioLinkageProps) {
    if (isLoading) {
        return (
            <div className="rounded-2xl border overflow-hidden" style={{ background: "linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)", borderColor: "#1e3a5f" }}>
                <div className="px-6 py-3 border-b flex items-center gap-2" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
                    <Users className="w-4 h-4 text-blue-400" />
                    <span className="text-[11px] font-black text-slate-300 uppercase tracking-wider">组合联动视角</span>
                </div>
                <div className="p-6 flex items-center justify-center text-slate-400 text-sm">
                    组合影响计算中...
                </div>
            </div>
        );
    }

    if (!impactData) return null;

    const rows = buildRows(impactData).slice(0, 4);
    const headlineWarning = impactData.warnings[0];

    return (
        <div className="rounded-2xl border overflow-hidden" style={{ background: "linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)", borderColor: "#1e3a5f" }}>
            <div className="px-6 py-3 border-b flex items-center gap-2" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
                <Users className="w-4 h-4 text-blue-400" />
                <span className="text-[11px] font-black text-slate-300 uppercase tracking-wider">组合联动视角</span>
                <span className="text-[10px] text-slate-500 ml-1">— 加仓 {ticker} {positionPct}% 对组合意味着什么</span>
            </div>

            <div className="p-6">
                {(headlineWarning || impactData.ai_suggestion) && (
                    <div className="mb-5 bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3">
                        <div className="flex items-start gap-2.5">
                            <AlertTriangle className="w-4 h-4 text-rose-300 shrink-0 mt-0.5" />
                            <p className="text-[11px] text-rose-200 leading-relaxed flex-1">
                                <span className="font-black">关键提示：</span>
                                {impactData.ai_suggestion || headlineWarning}
                            </p>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div>
                        <div className="flex items-baseline justify-between mb-3">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider">加仓后行业敞口变化</span>
                            <div className="flex items-center gap-3 text-[9px] text-slate-500">
                                <span className="flex items-center gap-1"><span className="w-2 h-1 bg-slate-500 rounded" />加仓前</span>
                                <span className="flex items-center gap-1"><span className="w-2 h-1.5 bg-amber-400 rounded" />加仓后</span>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {rows.map((row) => {
                                const colorSet = SECTOR_COLORS[row.sector] ?? SECTOR_COLORS.Unknown;
                                const label = SECTOR_LABELS[row.sector] ?? row.sector;

                                return (
                                    <div key={row.sector}>
                                        <div className="flex items-center justify-between mb-1.5">
                                            <span className="text-[11px] text-slate-200 font-semibold">
                                                {label} <span className="text-slate-500 uppercase">{row.sector}</span>
                                            </span>
                                            <div className="flex items-center gap-2 mono text-[10px]">
                                                <span className="text-slate-500">{row.currentWeight.toFixed(1)}%</span>
                                                <span className="text-slate-500">→</span>
                                                <span className={clsx("font-bold", row.isOverLimit ? "text-amber-400" : "text-slate-200")}>
                                                    {row.projectedWeight.toFixed(1)}%
                                                </span>
                                                <span className={clsx("ml-1", row.isOverLimit ? "text-rose-400 font-bold" : colorSet.text)}>
                                                    {formatDelta(row.currentWeight, row.projectedWeight)}
                                                </span>
                                            </div>
                                        </div>

                                        <div>
                                            <div className="h-1 bg-slate-700 rounded-full overflow-hidden relative">
                                                <div className={clsx("h-full rounded-full", colorSet.current)} style={{ width: `${row.currentWeight}%` }} />
                                                <div className="absolute top-[-3px] bottom-[-9px] w-px bg-rose-400/60" style={{ left: "40%" }} />
                                                <div className="absolute -top-3 mono text-[8px] text-rose-400" style={{ left: "40%", transform: "translateX(-50%)" }}>
                                                    40%
                                                </div>
                                            </div>
                                            <div className="h-2 bg-slate-700 rounded-full overflow-hidden mt-1 relative">
                                                <div className={clsx("h-full rounded-full", colorSet.projected)} style={{ width: `${row.projectedWeight}%` }} />
                                                <div className="absolute top-0 bottom-0 w-px bg-rose-400/60" style={{ left: "40%" }} />
                                            </div>
                                        </div>

                                        {row.isOverLimit && (
                                            <p className="text-[9px] text-rose-400 font-bold mt-1.5">
                                                ⚠ 加仓后超过 40% 建议上限
                                            </p>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div>
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-3">
                            组合关键指标影响
                        </div>

                        <div className="space-y-3">
                            <MetricRow
                                label="组合 Beta"
                                before={impactData.current_beta.toFixed(2)}
                                after={impactData.projected_beta.toFixed(2)}
                                tone={impactData.projected_beta > impactData.current_beta ? "amber" : "emerald"}
                                badge={impactData.projected_beta > impactData.current_beta ? "↑ 波动" : "↓ 稳健"}
                            />
                            <MetricRow
                                label="Sharpe 预期"
                                before={impactData.current_sharpe.toFixed(2)}
                                after={impactData.projected_sharpe.toFixed(2)}
                                tone={impactData.projected_sharpe >= impactData.current_sharpe ? "emerald" : "amber"}
                                badge={impactData.projected_sharpe >= impactData.current_sharpe ? "↑ 改善" : "↓ 承压"}
                            />
                            <div className="flex items-center justify-between py-2">
                                <span className="text-[11px] text-slate-400">建议最大仓位</span>
                                <span className="text-sm font-black text-blue-400 mono">
                                    {positionPct.toFixed(1)}% → {impactData.max_recommended_pct.toFixed(1)}%
                                </span>
                            </div>
                        </div>

                        {impactData.warnings.length > 0 && (
                            <div className="mt-4 space-y-1.5">
                                {impactData.warnings.map((warning, index) => (
                                    <div key={`${warning}-${index}`} className="flex items-center gap-1.5 text-[10px] text-amber-300">
                                        <AlertTriangle className="h-3 w-3" />
                                        <span>{warning}</span>
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

function MetricRow({
    label,
    before,
    after,
    tone,
    badge,
}: {
    label: string;
    before: string;
    after: string;
    tone: "amber" | "emerald";
    badge: string;
}) {
    const badgeClass = tone === "amber"
        ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
        : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";

    const valueClass = tone === "amber" ? "text-white" : "text-emerald-400";

    return (
        <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
            <span className="text-[11px] text-slate-400">{label}</span>
            <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 line-through mono">{before}</span>
                <span className={clsx("text-sm font-black mono", valueClass)}>{after}</span>
                <span className={clsx("text-[9px] font-black px-1.5 py-0.5 rounded border", badgeClass)}>
                    {badge}
                </span>
            </div>
        </div>
    );
}
