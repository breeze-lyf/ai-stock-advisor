"use client";

import React from "react";
import { Target, ShieldAlert, Wallet, TrendingUp } from "lucide-react";
import { PortfolioItem } from "@/types";
import type { AIData } from "./types";
import type { PositionImpactAnalysis } from "@/features/portfolio/risk-api";

interface PositionOverlayProps {
    selectedItem: PortfolioItem | null;
    aiData: AIData | null;
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
    positionImpact?: PositionImpactAnalysis | null;
}

function toPct(value: number) {
    return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export const PositionOverlay = React.memo(function PositionOverlay({
    selectedItem,
    aiData,
    currency,
    sanitizePrice,
    positionImpact,
}: PositionOverlayProps) {
    if (!selectedItem || (selectedItem.quantity || 0) <= 0) {
        return null;
    }

    const quantity = selectedItem.quantity || 0;
    const avgCost = selectedItem.avg_cost || 0;
    const currentPrice = selectedItem.current_price || 0;
    const marketValue = selectedItem.market_value || currentPrice * quantity;
    const sectorRows = (positionImpact?.current_sector_exposure || []).filter((row) =>
        Number.isFinite(row.value) && Number.isFinite(row.weight)
    );
    const sectorMatchedRow = selectedItem.sector
        ? sectorRows.find((row) => row.sector === selectedItem.sector)
        : undefined;
    const portfolioTotalFromRows = sectorRows.reduce((sum, row) => sum + row.value, 0);
    const portfolioTotalFromSector =
        sectorMatchedRow && sectorMatchedRow.weight > 0
            ? sectorMatchedRow.value / (sectorMatchedRow.weight / 100)
            : 0;
    const portfolioTotal = portfolioTotalFromRows > 0 ? portfolioTotalFromRows : portfolioTotalFromSector;
    const weight = portfolioTotal > 0 ? (marketValue / portfolioTotal) * 100 : 0;
    const pnlPct = avgCost > 0 ? ((currentPrice - avgCost) / avgCost) * 100 : 0;
    const stopLoss = aiData?.stop_loss_price;
    const entryLow = aiData?.entry_price_low;
    const entryHigh = aiData?.entry_price_high;
    const addOnTrigger = aiData?.add_on_trigger;
    const maxPositionPct = aiData?.max_position_pct;

    let positionAdvice = "当前仓位与公共分析计划基本一致，耐心等待下一触发点。";
    if (typeof stopLoss === "number" && currentPrice <= stopLoss) {
        positionAdvice = `当前价已接近/跌破计划止损 ${currency}${sanitizePrice(stopLoss)}，优先执行风控。`;
    } else if (typeof entryLow === "number" && typeof entryHigh === "number" && currentPrice >= entryLow && currentPrice <= entryHigh) {
        positionAdvice = `当前价仍处于计划建仓区 ${currency}${sanitizePrice(entryLow)}-${sanitizePrice(entryHigh)}，已有仓位可继续按原计划观察，不必追高。`;
    } else if (typeof entryHigh === "number" && currentPrice > entryHigh) {
        positionAdvice = `当前价已高于计划建仓区上沿 ${currency}${sanitizePrice(entryHigh)}，已有仓位以持有为主，等待加仓触发再动作。`;
    }

    let weightAdvice = "当前仓位占比可接受。";
    if (typeof maxPositionPct === "number" && maxPositionPct > 0) {
        if (weight > maxPositionPct) {
            weightAdvice = `当前持仓约 ${weight.toFixed(1)}%，高于建议上限 ${maxPositionPct.toFixed(0)}%，不宜继续加仓。`;
        } else {
            weightAdvice = `当前持仓约 ${weight.toFixed(1)}%，低于建议上限 ${maxPositionPct.toFixed(0)}%，仍保留机动空间。`;
        }
    }

    return (
        <section className="rounded-[2rem] border border-neutral-100 bg-white px-4 py-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 md:px-10">
            <div className="space-y-3.5">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-emerald-600 rounded-full shadow-[0_0_12px_rgba(5,150,105,0.45)]" />
                    <div>
                        <h2 className="text-xl font-black tracking-tight text-neutral-900 dark:text-neutral-100 uppercase">我的持仓建议</h2>
                        <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">基于你的实际成本与仓位，对公共分析结果做个性化管理补充。</p>
                    </div>
                </div>

                <div className="space-y-3.5">
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
                    {[
                        { label: "持仓数量", value: `${quantity}`, icon: Wallet },
                        { label: "持仓成本", value: `${currency}${sanitizePrice(avgCost)}`, icon: Target },
                        { label: "浮盈亏", value: toPct(pnlPct), icon: TrendingUp },
                        {
                            label: "仓位占比",
                            value: weight > 0 ? `${weight.toFixed(1)}%` : "--",
                            icon: ShieldAlert,
                        },
                    ].map((item) => {
                        const Icon = item.icon;
                        return (
                            <div key={item.label} className="rounded-[22px] border border-neutral-200 bg-neutral-50/80 px-4 py-4 dark:border-zinc-800 dark:bg-zinc-950/60">
                                <div className="flex items-center gap-2 text-neutral-400 dark:text-neutral-500">
                                    <Icon className="h-4 w-4" />
                                    <span className="text-[10px] font-black uppercase tracking-[0.18em]">{item.label}</span>
                                </div>
                                <div className="mt-2 text-lg font-black text-neutral-900 dark:text-white">{item.value}</div>
                            </div>
                        );
                    })}
                </div>

                <div className="grid gap-3 md:grid-cols-2 md:gap-4">
                    <div className="rounded-[22px] border border-emerald-200 bg-emerald-50/70 px-5 py-4 dark:border-emerald-900/50 dark:bg-emerald-950/20">
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">仓位动作建议</p>
                        <p className="mt-2 text-sm leading-7 text-neutral-700 dark:text-neutral-200">{positionAdvice}</p>
                    </div>
                    <div className="rounded-[22px] border border-blue-200 bg-blue-50/70 px-5 py-4 dark:border-blue-900/50 dark:bg-blue-950/20">
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">仓位约束</p>
                        <p className="mt-2 text-sm leading-7 text-neutral-700 dark:text-neutral-200">{weightAdvice}</p>
                        {addOnTrigger && (
                            <p className="mt-3 text-sm leading-7 text-neutral-600 dark:text-neutral-300">
                                <span className="font-bold text-neutral-900 dark:text-white">加仓触发：</span>
                                {addOnTrigger}
                            </p>
                        )}
                    </div>
                </div>
            </div>
            </div>
        </section>
    );
});
