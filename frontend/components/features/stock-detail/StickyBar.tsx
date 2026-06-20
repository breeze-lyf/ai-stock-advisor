/**
 * 粘性顶栏 (Sticky Navigation Bar)
 * 职责：当用户向下滚动超过阈值时，显示极简版的股票信息和快速操作按钮
 * 触发时机：容器 scrollTop > 80px
 */
"use client";

import React from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import { TrendingUp, RefreshCw, ChevronLeft } from "lucide-react";
import { StickyBarProps } from "./types";

export const StickyBar = React.memo(function StickyBar({
    selectedItem,
    isScrolled,
    refreshing,
    onRefresh,
    onBack,
    currency,
    sanitizePrice,
    activeTab,
    onTabChange,
}: StickyBarProps) {
    const tabs = [
        { key: "info" as const, label: "标的信息" },
        { key: "analysis" as const, label: "AI 分析" },
    ];
    return (
        <div className="sticky top-0 z-50 h-0 overflow-visible">
            <div className={clsx(
                "-mx-2 md:-mx-4 px-2 md:px-4 pt-2 transition-all duration-300",
                isScrolled ? "opacity-100 tranneutral-y-0 pointer-events-auto" : "opacity-0 -tranneutral-y-5 pointer-events-none"
            )}>
                <div className="flex md:items-center justify-between gap-4 min-h-14 rounded-[1.35rem] border border-neutral-200/80 dark:border-zinc-800 bg-white/92 dark:bg-zinc-950/92 backdrop-blur-2xl shadow-[0_20px_60px_rgba(15,23,42,0.10)] px-4 md:px-5 py-2.5">
                    <div className="flex items-center gap-2 md:gap-4 min-w-0">
                    {onBack && (
                        <button onClick={onBack} title="返回" aria-label="返回" className="lg:hidden p-1 -ml-1 rounded-full text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors">
                            <ChevronLeft className="h-6 w-6" />
                        </button>
                    )}
                    <div className="flex flex-col min-w-0">
                        <h1 className="text-lg font-black tracking-tighter text-neutral-900 dark:text-white leading-tight truncate">
                            {selectedItem.name || selectedItem.ticker}
                        </h1>
                        <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest leading-none">
                            {selectedItem.ticker}
                        </span>
                    </div>
                    
                    <div className="h-6 w-px bg-neutral-100 dark:bg-neutral-800 mx-1 hidden md:block" />

                    <div className="hidden md:flex items-center gap-2">
                        <div className="flex flex-col items-end rounded-xl border border-neutral-100 dark:border-zinc-800 bg-neutral-50/80 dark:bg-zinc-900 px-3 py-1.5 shadow-sm">
                            <span className="text-[9px] font-black text-neutral-400 uppercase tracking-wider">现价</span>
                            <span className="text-lg font-black text-neutral-800 dark:text-neutral-100 tabular-nums leading-none">
                                {currency}{sanitizePrice(selectedItem.current_price)}
                            </span>
                        </div>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 rounded-full text-neutral-400 hover:text-blue-600 hover:bg-blue-600/10 transition-all duration-300"
                            onClick={onRefresh}
                            disabled={refreshing}
                            title="刷新行情"
                        >
                            <RefreshCw className={clsx("h-3.5 w-3.5", refreshing && "animate-spin")} />
                        </Button>
                        {selectedItem.quantity > 0 && (
                            <div className={clsx(
                                "flex items-center gap-1 px-2.5 py-1 rounded-xl text-[10px] font-black border",
                                (selectedItem.pl_percent || 0) >= 0 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-600/10 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-600/10 dark:text-rose-400"
                            )}>
                                <TrendingUp className={clsx("h-3 w-3", (selectedItem.pl_percent || 0) < 0 && "rotate-180")} />
                                {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                            </div>
                        )}
                        {selectedItem.market_status === "PRE_MARKET" && (
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-orange-100 dark:bg-orange-600/10 text-orange-600 dark:text-orange-400 font-black border border-orange-200 dark:border-orange-600/20 leading-none">
                                PRE
                            </span>
                        )}
                        {selectedItem.market_status === "AFTER_HOURS" && (
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-neutral-100 dark:bg-neutral-500/10 text-neutral-500 dark:text-neutral-400 font-black border border-neutral-200 dark:border-neutral-500/20 leading-none">
                                POST
                            </span>
                        )}
                    </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                        <div className="hidden lg:flex flex-col items-end rounded-xl border border-neutral-100 dark:border-zinc-800 bg-neutral-50/80 dark:bg-zinc-900 px-3 py-1.5 shadow-sm">
                            <span className="text-[10px] font-black uppercase text-neutral-400 tracking-tighter">最新增幅</span>
                            <span className={clsx("text-sm font-black tabular-nums", (selectedItem.change_percent || 0) >= 0 ? "text-emerald-600" : "text-rose-600")}>
                                {(selectedItem.change_percent || 0) >= 0 ? "+" : ""}{(selectedItem.change_percent || 0).toFixed(2)}%
                            </span>
                        </div>

                        {/* 粘性顶栏内的 Tab 切换 */}
                        {onTabChange && (
                            <div className="flex items-center bg-neutral-100 dark:bg-zinc-800 rounded-xl p-1 gap-1 shadow-sm">
                                {tabs.map(({ key, label }) => (
                                    <button
                                        key={key}
                                        onClick={() => onTabChange(key)}
                                        className={clsx(
                                            "px-3 py-1.5 text-[11px] font-semibold rounded-lg transition-all duration-150",
                                            activeTab === key
                                                ? "bg-white dark:bg-zinc-900 text-neutral-800 dark:text-neutral-100 shadow-sm"
                                                : "text-neutral-400 dark:text-neutral-500 hover:text-neutral-600"
                                        )}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
});
