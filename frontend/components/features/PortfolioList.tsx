"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Pencil, Trash2, Filter, X, RefreshCw } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import clsx from "clsx";
import { PortfolioItem } from "@/types";
import { addPortfolioItem, deletePortfolioItem, refreshStock, refreshAllStocks } from "@/lib/api";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface PortfolioListProps {
    portfolio: PortfolioItem[];
    selectedTicker: string | null;
    onSelectTicker: (ticker: string) => void;
    onRefresh: () => void;
    onOpenSearch: () => void;
    onlyHoldings: boolean;
    onToggleOnlyHoldings: (val: boolean) => void;
}

export function PortfolioList({
    portfolio,
    selectedTicker,
    onSelectTicker,
    onRefresh,
    onOpenSearch,
    onlyHoldings,
    onToggleOnlyHoldings,
}: PortfolioListProps) {
    const [editingTicker, setEditingTicker] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ quantity: "", cost: "" });
    const [sortBy, setSortBy] = useState<"ticker" | "price" | "change">("ticker");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

    const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null);
    const [isRefreshingAll, setIsRefreshingAll] = useState(false);

    const sortedPortfolio = [...portfolio]
        .filter((item) => !onlyHoldings || item.quantity > 0)
        .sort((a, b) => {
            let valA, valB;
            if (sortBy === "ticker") {
                valA = a.ticker;
                valB = b.ticker;
            } else if (sortBy === "price") {
                valA = a.current_price;
                valB = b.current_price;
            } else {
                valA = a.pl_percent;
                valB = b.pl_percent;
            }

            if (valA < valB) return sortOrder === "asc" ? -1 : 1;
            if (valA > valB) return sortOrder === "asc" ? 1 : -1;
            return 0;
        });

    const handleSort = (key: "ticker" | "price" | "change") => {
        if (sortBy === key) {
            setSortOrder(sortOrder === "asc" ? "desc" : "asc");
        } else {
            setSortBy(key);
            setSortOrder("asc");
        }
    };

    const handleUpdateItem = async (ticker: string) => {
        try {
            await addPortfolioItem(
                ticker,
                parseFloat(editForm.quantity) || 0,
                parseFloat(editForm.cost) || 0
            );
            onRefresh();
            setEditingTicker(null);
        } catch (err) {
            alert("更新失败");
        }
    };

    const handleDeleteItem = async (ticker: string) => {
        try {
            await deletePortfolioItem(ticker);
            onRefresh();
        } catch (err) {
            alert("删除失败");
        }
    };

    const handleRefreshItem = async (ticker: string) => {
        setRefreshingTicker(ticker);
        try {
            await refreshStock(ticker);
            onRefresh();
        } catch (err) {
            console.error("Refresh failed", err);
        } finally {
            setRefreshingTicker(null);
        }
    };

    return (
        <div className="col-span-3 border-r bg-white dark:bg-slate-900 flex flex-col h-full overflow-hidden">
            <div className="py-3 px-4 border-b font-medium text-sm text-slate-500 flex justify-between items-center bg-slate-50/50">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-700 dark:text-slate-300">股票列表</span>
                    <Button
                        variant={onlyHoldings ? "secondary" : "ghost"}
                        size="icon"
                        className="h-6 w-6"
                        title="只看持仓"
                        onClick={() => onToggleOnlyHoldings(!onlyHoldings)}
                    >
                        <Filter className={clsx("h-3 w-3", onlyHoldings && "text-blue-500")} />
                    </Button>
                </div>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-slate-400 hover:text-blue-500"
                        title="刷新全部"
                        onClick={async () => {
                            if (isRefreshingAll) return;
                            setIsRefreshingAll(true);
                            try {
                                const res = await refreshAllStocks();
                                console.log(res.message);
                                onRefresh();
                            } catch (err) {
                                console.error("Refresh all failed", err);
                                alert("刷新失败");
                            } finally {
                                setIsRefreshingAll(false);
                            }
                        }}
                        disabled={isRefreshingAll}
                    >
                        <RefreshCw className={clsx("h-3.5 w-3.5", isRefreshingAll && "animate-spin text-blue-500")} />
                    </Button>
                    <Button
                    variant="outline"
                    size="icon"
                    className="h-6 w-6"
                    onClick={onOpenSearch}
                >
                    <Plus className="h-4 w-4" />
                </Button>
                </div>
            </div>

            {/* Table Headers */}
            <div className="grid grid-cols-3 px-4 py-1.5 border-b text-[10px] uppercase tracking-wider font-bold text-slate-400 bg-slate-50/50 dark:bg-slate-800/20">
                <div
                    className="cursor-pointer hover:text-blue-500 transition-colors flex items-center gap-1"
                    onClick={() => handleSort("ticker")}
                >
                    代码 {sortBy === "ticker" && (sortOrder === "asc" ? "↑" : "↓")}
                </div>
                <div
                    className="cursor-pointer hover:text-blue-500 transition-colors flex items-center justify-center gap-1"
                    onClick={() => handleSort("price")}
                >
                    价格 {sortBy === "price" && (sortOrder === "asc" ? "↑" : "↓")}
                </div>
                <div
                    className="cursor-pointer hover:text-blue-500 transition-colors flex items-center justify-end gap-1"
                    onClick={() => handleSort("change")}
                >
                    涨幅 {sortBy === "change" && (sortOrder === "asc" ? "↑" : "↓")}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {sortedPortfolio.map((item) => (
                    <div
                        key={item.ticker}
                        className={clsx(
                            "border-b transition-all duration-200",
                            selectedTicker === item.ticker
                                ? "bg-blue-50/50 dark:bg-blue-900/10 border-l-4 border-l-blue-500"
                                : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        )}
                    >
                        <div
                            onClick={() => onSelectTicker(item.ticker)}
                            className="py-2.5 px-4 cursor-pointer relative group"
                        >
                            <div className="grid grid-cols-3 items-center mb-1">
                                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                                        <div className="flex flex-col truncate">
                                            <span className="font-bold text-sm text-slate-900 dark:text-slate-100 leading-tight truncate">
                                                {item.ticker}
                                            </span>
                                            {item.name && (
                                                <span className="text-[10px] text-slate-400 font-bold tracking-tight truncate">
                                                    {item.name}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center justify-center gap-1.5">
                                        <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                                            ${item.current_price.toFixed(2)}
                                        </span>
                                        {item.risk_reward_ratio !== null && item.risk_reward_ratio !== undefined && (
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <div className={clsx(
                                                        "shrink-0 w-7 h-4 flex items-center justify-center rounded-[4px] border cursor-help transition-colors",
                                                        item.risk_reward_ratio >= 3.0 ? "bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/20" :
                                                        item.risk_reward_ratio >= 1.5 ? "bg-blue-500/10 border-blue-500/20 hover:bg-blue-500/20" :
                                                        "bg-rose-500/10 border-rose-500/20 hover:bg-rose-500/20"
                                                    )}>
                                                        <span className={clsx(
                                                            "text-[8px] font-black tabular-nums leading-none",
                                                            item.risk_reward_ratio >= 3.0 ? "text-emerald-600 dark:text-emerald-400" :
                                                            item.risk_reward_ratio >= 1.5 ? "text-blue-600 dark:text-blue-400" :
                                                            "text-rose-600 dark:text-rose-400"
                                                        )}>
                                                            {item.risk_reward_ratio.toFixed(1)}
                                                        </span>
                                                    </div>
                                                </TooltipTrigger>
                                                <TooltipContent className="bg-white dark:bg-slate-900 border-2 border-slate-100 dark:border-slate-800 p-3 shadow-xl z-50">
                                                    <div className="flex flex-col gap-1.5">
                                                        <div className="flex items-center justify-between gap-4">
                                                            <span className="text-[10px] font-black uppercase text-slate-400">盈亏比 (RRR)</span>
                                                            <span className={clsx(
                                                                "text-sm font-black italic",
                                                                item.risk_reward_ratio >= 3.0 ? "text-emerald-500" :
                                                                item.risk_reward_ratio >= 1.5 ? "text-blue-500" :
                                                                "text-rose-500"
                                                            )}>
                                                                {item.risk_reward_ratio.toFixed(2)}
                                                            </span>
                                                        </div>
                                                        <div className="h-px bg-slate-100 dark:bg-slate-800 my-0.5" />
                                                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                                            <div className="flex flex-col">
                                                                <span className="text-[8px] font-bold text-slate-400 uppercase">关键阻力 (R1/Target)</span>
                                                                <span className="text-[11px] font-black tabular-nums">${item.resistance_1?.toFixed(2)}</span>
                                                            </div>
                                                            <div className="flex flex-col">
                                                                <span className="text-[8px] font-bold text-slate-400 uppercase">关键支撑 (S1/Stop)</span>
                                                                <span className="text-[11px] font-black tabular-nums">${item.support_1?.toFixed(2)}</span>
                                                            </div>
                                                        </div>
                                                        <p className="text-[9px] text-slate-400 italic mt-1 leading-tight max-w-[150px]">
                                                            {item.risk_reward_ratio >= 3.0 ? "高盈亏比机会" : 
                                                             item.risk_reward_ratio >= 1.5 ? "稳健交易机会" : "低盈亏比/风险较高"}：潜在收益是风险的 {item.risk_reward_ratio.toFixed(1)} 倍
                                                        </p>
                                                    </div>
                                                </TooltipContent>
                                            </Tooltip>
                                        )}
                                    </div>
                                <span
                                    className={clsx(
                                        "text-right text-xs font-bold",
                                        (item.change_percent || 0) >= 0 ? "text-green-600" : "text-red-500"
                                    )}
                                >
                                    {(item.change_percent || 0) >= 0 ? "+" : ""}
                                    {(item.change_percent || 0).toFixed(2)}%
                                </span>
                            </div>
                            <div className="flex justify-between items-end mt-0.5">
                                <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2">
                                    {item.quantity > 0 ? (
                                        <>
                                            <span className="bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 px-1 rounded font-bold border border-green-100 dark:border-green-800">
                                                HOLD {item.quantity}
                                            </span>
                                            <span className="text-slate-300 dark:text-slate-600">|</span>
                                            <span>AVG: {item.avg_cost.toFixed(2)}</span>
                                        </>
                                    ) : (
                                        <span className="text-slate-300 italic">WATCHING</span>
                                    )}
                                    {item.last_updated && (
                                        <>
                                            <span className="text-slate-300 dark:text-slate-600">|</span>
                                            <span className="text-[9px] opacity-60">
                                                更新于{" "}
                                                {formatDistanceToNow(new Date(item.last_updated + "Z"), {
                                                    addSuffix: true,
                                                    locale: zhCN,
                                                })}
                                            </span>
                                        </>
                                    )}
                                </div>
                                <div
                                    className={clsx(
                                        "flex gap-1 transition-opacity",
                                        editingTicker === item.ticker || refreshingTicker === item.ticker
                                            ? "opacity-100"
                                            : "opacity-0 group-hover:opacity-100"
                                    )}
                                >
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className={clsx(
                                            "h-7 w-7",
                                            refreshingTicker === item.ticker
                                                ? "text-blue-500 bg-blue-50"
                                                : "text-slate-300 hover:text-blue-500 hover:bg-blue-50"
                                        )}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleRefreshItem(item.ticker);
                                        }}
                                        disabled={refreshingTicker === item.ticker}
                                    >
                                        <RefreshCw className={clsx("h-3.5 w-3.5", refreshingTicker === item.ticker && "animate-spin")} />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className={clsx(
                                            "h-7 w-7",
                                            editingTicker === item.ticker
                                                ? "text-blue-500 bg-blue-50"
                                                : "text-slate-300 hover:text-blue-500 hover:bg-blue-50"
                                        )}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            if (editingTicker === item.ticker) {
                                                setEditingTicker(null);
                                            } else {
                                                setEditingTicker(item.ticker);
                                                setEditForm({
                                                    quantity: item.quantity.toString(),
                                                    cost: item.avg_cost.toString(),
                                                });
                                            }
                                        }}
                                    >
                                        <Pencil className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-slate-300 hover:text-red-500 hover:bg-red-50"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteItem(item.ticker);
                                        }}
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {editingTicker === item.ticker && (
                            <div
                                className="px-4 pb-4 animate-in slide-in-from-top-1 duration-200"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="flex items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                                    <div className="flex items-center gap-1.5 flex-1">
                                        <div className="relative flex-1">
                                            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-bold">
                                                持
                                            </span>
                                            <Input
                                                type="number"
                                                className="h-7 text-[11px] pl-6 pr-1 bg-white dark:bg-slate-900 border-slate-200 focus:border-blue-400 transition-colors shadow-none"
                                                value={editForm.quantity}
                                                onChange={(e) =>
                                                    setEditForm({ ...editForm, quantity: e.target.value })
                                                }
                                            />
                                        </div>
                                        <div className="relative flex-1">
                                            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-bold">
                                                均
                                            </span>
                                            <Input
                                                type="number"
                                                className="h-7 text-[11px] pl-6 pr-1 bg-white dark:bg-slate-900 border-slate-200 focus:border-blue-400 transition-colors shadow-none"
                                                value={editForm.cost}
                                                onChange={(e) =>
                                                    setEditForm({ ...editForm, cost: e.target.value })
                                                }
                                            />
                                        </div>
                                    </div>
                                    <Button
                                        size="sm"
                                        className="h-7 px-3 bg-blue-600 hover:bg-blue-700 text-[11px] font-bold"
                                        onClick={() => handleUpdateItem(item.ticker)}
                                    >
                                        确定
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-slate-300 hover:text-slate-500"
                                        onClick={() => setEditingTicker(null)}
                                    >
                                        <X className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
                {sortedPortfolio.length === 0 && (
                    <div className="p-12 text-center text-slate-400 text-sm italic">列表为空</div>
                )}
            </div>
        </div>
    );
}
