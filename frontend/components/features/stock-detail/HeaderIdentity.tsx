/**
 * 股票身份头 (Header Identity)
 * 职责：展示股票名称、实时价格、涨跌幅、持仓信息
 * 当页面滚动时淡出，将空间让给粘性顶栏
 */
"use client";

import React from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import { RefreshCw, ChevronLeft } from "lucide-react";
import { HeaderIdentityProps } from "./types";

export const HeaderIdentity = React.memo(function HeaderIdentity({
    selectedItem,
    isScrolled,
    refreshing,
    onRefresh,
    onBack,
    activeTab = "info",
    onTabChange,
}: HeaderIdentityProps) {
    const tabs = [
        { key: "info" as const, label: "标的信息" },
        { key: "analysis" as const, label: "AI 分析" },
    ];

    return (
        <div className={clsx(
            "flex flex-col gap-2 transition-all duration-500",
            isScrolled && "opacity-0 pointer-events-none"
        )}>
            <div className="flex flex-col sm:flex-row justify-between sm:items-end gap-3 sm:gap-4">
                <div className="flex items-start gap-2">
                    {onBack && (
                        <button onClick={onBack} title="返回" aria-label="返回" className="lg:hidden mt-1 p-1 -ml-1 rounded-full text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
                            <ChevronLeft className="h-7 w-7" />
                        </button>
                    )}
                    <div className="flex flex-col">
                        <div className="flex items-center gap-3">
                            <h1 className="text-3xl md:text-4xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                                {selectedItem.name || selectedItem.ticker}
                            </h1>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 rounded-full text-slate-400 hover:text-blue-600 hover:bg-blue-600/10 transition-all duration-300"
                                onClick={onRefresh}
                                disabled={refreshing}
                                title="刷新行情"
                            >
                                <RefreshCw className={clsx("h-4 w-4", refreshing && "animate-spin")} />
                            </Button>
                        </div>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mt-2">
                            {selectedItem.name ? selectedItem.ticker : "全维度财务声誉分析"}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-6 sm:gap-10">
                    {/* 最新涨跌 (Daily Change) */}
                    <div className="hidden sm:flex flex-col items-end">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">最新涨跌</span>
                        <span className={clsx("text-lg font-black tabular-nums", (selectedItem.change_percent || 0) >= 0 ? "text-emerald-600" : "text-rose-600")}>
                            {(selectedItem.change_percent || 0) >= 0 ? "+" : ""}{selectedItem.change_percent?.toFixed(2)}%
                        </span>
                    </div>

                    {/* 实时价格 */}
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-3xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                            ${selectedItem.current_price.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            {/* 持仓信息（仅当持有时显示） */}
            {selectedItem.quantity > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 pt-3 border-t border-slate-50 dark:border-slate-800/50">
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">持有仓位</span>
                        <span className="text-md font-bold text-slate-700 dark:text-slate-300">{selectedItem.quantity} Shares</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">持仓均价</span>
                        <span className="text-md font-bold text-slate-700 dark:text-slate-300">${selectedItem.avg_cost.toFixed(2)}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">账面盈亏</span>
                        <div className="flex items-center gap-2">
                            <span className={clsx("text-md font-bold", selectedItem.unrealized_pl >= 0 ? "text-emerald-600" : "text-rose-600")}>
                                {selectedItem.unrealized_pl >= 0 ? "+" : ""}${selectedItem.unrealized_pl.toFixed(2)}
                            </span>
                            <span className={clsx(
                                "text-[10px] font-black px-1.5 py-0.5 rounded-md",
                                selectedItem.pl_percent >= 0 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-600/10 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-600/10 dark:text-rose-400"
                            )}>
                                {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                </div>
            )}
        {/* Tab 导航 — 融合在标题栏底部，下划线风格 */}
        {onTabChange && (
            <div className="flex border-b border-slate-100 dark:border-zinc-800 mt-1">
                {tabs.map(({ key, label }) => (
                    <button
                        key={key}
                        onClick={() => onTabChange(key)}
                        className={clsx(
                            "relative px-4 py-2.5 text-sm font-semibold transition-colors duration-200",
                            activeTab === key
                                ? "text-slate-900 dark:text-white"
                                : "text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
                        )}
                    >
                        {label}
                        {activeTab === key && (
                            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 dark:bg-white rounded-full" />
                        )}
                    </button>
                ))}
            </div>
        )}
        </div>
    );
});
