"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import clsx from "clsx";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import { PortfolioItem } from "@/types";
import { addPortfolioItem, deletePortfolioItem, refreshStock, refreshAllStocks, reorderPortfolio } from "@/lib/api";
import { ArrowUpToLine, Plus, Pencil, Trash2, Filter, X, RefreshCw } from "lucide-react";
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
    fullView?: boolean; // 新增：全屏模式开关
}

export function PortfolioList({
    portfolio,
    selectedTicker,
    onSelectTicker,
    onRefresh,
    onOpenSearch,
    onlyHoldings,
    onToggleOnlyHoldings,
    fullView = false, // 默认为窄边栏模式
}: PortfolioListProps) {
    const [editingTicker, setEditingTicker] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ quantity: "", cost: "" });
    const [sortBy, setSortBy] = useState<"ticker" | "price" | "change" | "manual" | "risk_reward_ratio">("manual");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

    const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null);
    const [deletingTicker, setDeletingTicker] = useState<string | null>(null);
    const [isRefreshingAll, setIsRefreshingAll] = useState(false);

    const getCurrencySymbol = (ticker: string) => {
        const isCN = /^\d{6}/.test(ticker) || ticker.toUpperCase().endsWith('.SS') || ticker.toUpperCase().endsWith('.SZ');
        return isCN ? "¥" : "$";
    };

    const sortedPortfolio = [...portfolio]
        .filter((item) => !onlyHoldings || item.quantity > 0)
        .sort((a, b) => {
            let valA, valB;
            if (sortBy === "risk_reward_ratio") {
                valA = a.risk_reward_ratio;
                valB = b.risk_reward_ratio;
            } else if (sortBy === "ticker") {
                valA = a.ticker;
                valB = b.ticker;
            } else if (sortBy === "price") {
                valA = a.current_price;
                valB = b.current_price;
            } else if (sortBy === "change") {
                valA = a.change_percent;
                valB = b.change_percent;
            } else {
                // 默认手动排序 (Manual sort based on sort_order)
                return 0; // 由于后端已经排好序返回，且前端没有重排逻辑时，保持原序
            }

            if (valA === null || valB === null || valA === undefined || valB === undefined) return 0;

            if (valA < valB) return sortOrder === "asc" ? -1 : 1;
            if (valA > valB) return sortOrder === "asc" ? 1 : -1;
            return 0;
        });

    const handleSort = (key: "ticker" | "price" | "change" | "manual" | "risk_reward_ratio") => {
        if (sortBy === key) {
            setSortOrder(sortOrder === "asc" ? "desc" : "asc");
        } else {
            setSortBy(key);
            // 盈亏比及涨幅默认从高到低排列
            setSortOrder(key === "risk_reward_ratio" || key === "change" ? "desc" : "asc");
        }
    };

    const handlePinToTop = async (ticker: string) => {
        // 将选中的股票排到第一，其余顺延
        const others = portfolio.filter(p => p.ticker !== ticker);
        const newOrders = [
            { ticker, sort_order: 0 },
            ...others.map((p, idx) => ({ ticker: p.ticker, sort_order: idx + 1 }))
        ];

        try {
            await reorderPortfolio(newOrders);
            onRefresh();
            setSortBy("manual"); // 强制切换回手动排序视图
        } catch (err) {
            alert("排序更新失败");
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
        if (deletingTicker) return;
        setDeletingTicker(ticker);
        try {
            await deletePortfolioItem(ticker);
            // 只有当 API 真正返回成功（或至少没有抛错）时才执行
            onRefresh();
        } catch (err: any) {
            // 如果是 404，说明已经删除了，不应该报错
            if (err.response?.status !== 404) {
                alert("删除失败");
            } else {
                onRefresh();
            }
        } finally {
            setDeletingTicker(null);
        }
    };

    const handleRefreshItem = async (ticker: string) => {
        setRefreshingTicker(ticker);
        try {
            // 侧边栏列表默认使用“价格模式”
            await refreshStock(ticker, true);
            onRefresh();
        } catch (err) {
            console.error("Refresh failed", err);
        } finally {
            setRefreshingTicker(null);
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden">
            <div className="py-3 px-4 border-b border-slate-100 dark:border-zinc-800 font-medium text-sm text-slate-500 flex justify-between items-center bg-slate-50/50 dark:bg-zinc-900/50">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-700 dark:text-slate-300">股票列表</span>
                    <Button
                        variant={onlyHoldings ? "secondary" : "ghost"}
                        size="icon"
                        className="h-6 w-6"
                        title="只看持仓"
                        onClick={() => onToggleOnlyHoldings(!onlyHoldings)}
                    >
                        <Filter className={clsx("h-3 w-3", onlyHoldings && "text-blue-600")} />
                    </Button>
                </div>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-slate-400 hover:text-blue-600"
                        title="刷新全部"
                        onClick={async () => {
                            if (isRefreshingAll) return;
                            setIsRefreshingAll(true);
                            try {
                                // 侧边栏列表默认使用“价格模式”，极速响应
                                const res = await refreshAllStocks(true);
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
                        <RefreshCw className={clsx("h-3.5 w-3.5", isRefreshingAll && "animate-spin text-blue-600")} />
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
            <div className="grid grid-cols-4 px-4 py-1.5 border-b border-slate-100 dark:border-zinc-800 text-[10px] uppercase tracking-wider font-bold text-slate-400 bg-slate-50/50 dark:bg-zinc-900/50">
                <div
                    className="cursor-pointer hover:text-blue-600 transition-colors flex items-center gap-1"
                    onClick={() => handleSort(sortBy === "manual" ? "ticker" : "manual")}
                >
                    {sortBy === "manual" ? "默认" : "代码"}{" "}
                    {sortBy === "manual" ? "" : (sortBy === "ticker" ? (sortOrder === "asc" ? "↑" : "↓") : "")}
                </div>
                <div
                    className="cursor-pointer hover:text-blue-600 transition-colors flex items-center justify-center gap-1"
                    onClick={() => handleSort("price")}
                >
                    价格 {sortBy === "price" && (sortOrder === "asc" ? "↑" : "↓")}
                </div>
                <div
                    className="cursor-pointer hover:text-blue-600 transition-colors flex items-center justify-center gap-1"
                    onClick={() => handleSort("risk_reward_ratio")}
                >
                    盈亏比 {sortBy === "risk_reward_ratio" && (sortOrder === "asc" ? "↑" : "↓")}
                </div>
                <div
                    className="cursor-pointer hover:text-blue-600 transition-colors flex items-center justify-end gap-1"
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
                            "border-b border-slate-100 dark:border-zinc-800/80 transition-all duration-200",
                            selectedTicker === item.ticker
                                ? "bg-blue-50/50 dark:bg-blue-900/10 border-l-4 border-l-blue-600"
                                : "hover:bg-slate-50 dark:hover:bg-zinc-800/30"
                        )}
                    >
                        <div
                            onClick={() => onSelectTicker(item.ticker)}
                            className="py-2.5 px-4 cursor-pointer relative group"
                        >
                            <div className="grid grid-cols-4 items-center mb-1">
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
                                    
                                    <div className="flex flex-col items-center">
                                        <div className="flex items-center justify-center gap-1">
                                            <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                                                {getCurrencySymbol(item.ticker)}{item.current_price.toFixed(2)}
                                            </span>
                                            {item.market_status === "PRE_MARKET" && (
                                                <span className="text-[8px] px-1 rounded-sm bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 font-black border border-orange-200 dark:border-orange-500/20 leading-none py-0.5">
                                                    PRE
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex flex-col items-center">
                                        {item.risk_reward_ratio !== null && item.risk_reward_ratio !== undefined ? (
                                            <div className={clsx(
                                                "shrink-0 w-8 h-4 flex items-center justify-center rounded-[4px] border",
                                                item.risk_reward_ratio >= 3.0 ? "bg-emerald-600/10 border-emerald-600/20" :
                                                item.risk_reward_ratio >= 1.5 ? "bg-blue-600/10 border-blue-600/20" :
                                                "bg-rose-600/10 border-rose-600/20"
                                            )}>
                                                <span className={clsx(
                                                    "text-[9px] font-black tabular-nums leading-none",
                                                    item.risk_reward_ratio >= 3.0 ? "text-emerald-600 dark:text-emerald-400" :
                                                    item.risk_reward_ratio >= 1.5 ? "text-blue-600 dark:text-blue-400" :
                                                    "text-rose-600 dark:text-rose-400"
                                                )}>
                                                    {item.risk_reward_ratio.toFixed(1)}
                                                </span>
                                            </div>
                                        ) : (
                                            <span className="text-[10px] text-slate-300">--</span>
                                        )}
                                    </div>

                                    <div className="flex flex-col items-end">
                                        <span className={clsx(
                                            "text-sm font-bold tabular-nums",
                                            (item.change_percent || 0) >= 0 ? "text-emerald-600" : "text-rose-600"
                                        )}>
                                            {(item.change_percent || 0) >= 0 ? "+" : ""}
                                            {(item.change_percent || 0).toFixed(2)}%
                                        </span>
                                    </div>
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
                                        className="h-7 w-7 text-slate-300 hover:text-indigo-500 hover:bg-indigo-50"
                                        title="置顶"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handlePinToTop(item.ticker);
                                        }}
                                    >
                                        <ArrowUpToLine className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className={clsx(
                                            "h-7 w-7",
                                            refreshingTicker === item.ticker
                                                ? "text-blue-600 bg-blue-50"
                                                : "text-slate-300 hover:text-blue-600 hover:bg-blue-50"
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
                                                ? "text-blue-600 bg-blue-50"
                                                : "text-slate-300 hover:text-blue-600 hover:bg-blue-50"
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
                                        className={clsx(
                                            "h-7 w-7",
                                            deletingTicker === item.ticker
                                                ? "text-rose-600 bg-rose-50"
                                                : "text-slate-300 hover:text-rose-600 hover:bg-rose-50"
                                        )}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteItem(item.ticker);
                                        }}
                                        disabled={deletingTicker === item.ticker}
                                    >
                                        <Trash2 className={clsx("h-3.5 w-3.5", deletingTicker === item.ticker && "animate-pulse")} />
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
