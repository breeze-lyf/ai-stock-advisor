"use client";

import React from "react";
import { Target, ShieldAlert, Wallet, TrendingUp } from "lucide-react";
import { PortfolioItem } from "@/types";
import type { AIData } from "./types";

interface PositionOverlayProps {
    selectedItem: PortfolioItem | null;
    aiData: AIData | null;
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
}

function toPct(value: number) {
    return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export const PositionOverlay = React.memo(function PositionOverlay({
    selectedItem,
    aiData,
    currency,
    sanitizePrice,
}: PositionOverlayProps) {
    if (!selectedItem || (selectedItem.quantity || 0) <= 0) {
        return null;
    }

    const quantity = selectedItem.quantity || 0;
    const avgCost = selectedItem.avg_cost || 0;
    const currentPrice = selectedItem.current_price || 0;
    const marketValue = selectedItem.market_value || currentPrice * quantity;
    const weight = selectedItem.weight || 0;
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
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="h-8 w-1.5 bg-emerald-600 rounded-full shadow-[0_0_12px_rgba(5,150,105,0.45)]" />
                <div>
                    <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">我的持仓建议</h2>
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">基于你的实际成本与仓位，对公共分析结果做个性化管理补充。</p>
                </div>
            </div>

            <div className="px-4 md:px-10 space-y-5">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: "持仓数量", value: `${quantity}`, icon: Wallet },
                        { label: "持仓成本", value: `${currency}${sanitizePrice(avgCost)}`, icon: Target },
                        { label: "浮盈亏", value: toPct(pnlPct), icon: TrendingUp },
                        {
                            label: "仓位占比",
                            value: weight ? `${weight.toFixed(1)}%` : `${currency}${sanitizePrice(marketValue)}`,
                            icon: ShieldAlert,
                        },
                    ].map((item) => {
                        const Icon = item.icon;
                        return (
                            <div key={item.label} className="rounded-2xl border border-slate-200 dark:border-zinc-800 bg-slate-50/70 dark:bg-zinc-900 px-4 py-4">
                                <div className="flex items-center gap-2 text-slate-400 dark:text-slate-500">
                                    <Icon className="h-4 w-4" />
                                    <span className="text-[10px] font-black uppercase tracking-[0.18em]">{item.label}</span>
                                </div>
                                <div className="mt-2 text-lg font-black text-slate-900 dark:text-white">{item.value}</div>
                            </div>
                        );
                    })}
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 dark:border-emerald-900/50 dark:bg-emerald-950/20 px-5 py-4">
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">仓位动作建议</p>
                        <p className="mt-2 text-sm leading-7 text-slate-700 dark:text-slate-200">{positionAdvice}</p>
                    </div>
                    <div className="rounded-2xl border border-blue-200 bg-blue-50/70 dark:border-blue-900/50 dark:bg-blue-950/20 px-5 py-4">
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">仓位约束</p>
                        <p className="mt-2 text-sm leading-7 text-slate-700 dark:text-slate-200">{weightAdvice}</p>
                        {addOnTrigger && (
                            <p className="mt-3 text-sm leading-7 text-slate-600 dark:text-slate-300">
                                <span className="font-bold text-slate-900 dark:text-white">加仓触发：</span>
                                {addOnTrigger}
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
});
