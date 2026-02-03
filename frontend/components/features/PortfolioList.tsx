"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Pencil, Trash2, Filter, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import clsx from "clsx";
import { PortfolioItem } from "@/types";
import { addPortfolioItem, deletePortfolioItem } from "@/lib/api";

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
            if (selectedTicker === ticker) {
                // Parent should handle this if needed, but onRefresh will update props
            }
        } catch (err) {
            alert("删除失败");
        }
    };

    return (
        <div className="col-span-3 border-r bg-white dark:bg-slate-900 flex flex-col h-full overflow-hidden">
            <div className="p-4 border-b font-medium text-sm text-slate-500 flex justify-between items-center bg-slate-50/50">
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
                <Button
                    variant="outline"
                    size="icon"
                    className="h-6 w-6"
                    onClick={onOpenSearch}
                >
                    <Plus className="h-4 w-4" />
                </Button>
            </div>

            {/* Table Headers */}
            <div className="grid grid-cols-3 px-4 py-2 border-b text-[10px] uppercase tracking-wider font-bold text-slate-400 bg-slate-50/50 dark:bg-slate-800/20">
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
                            className="p-4 cursor-pointer relative group"
                        >
                            <div className="grid grid-cols-3 items-center mb-1">
                                <span className="font-bold text-sm text-slate-700 dark:text-slate-300">
                                    {item.ticker}
                                </span>
                                <span className="text-center font-mono text-xs text-slate-600 dark:text-slate-400">
                                    ${item.current_price.toFixed(2)}
                                </span>
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
                            <div className="flex justify-between items-end mt-1">
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
                                        editingTicker === item.ticker
                                            ? "opacity-100"
                                            : "opacity-0 group-hover:opacity-100"
                                    )}
                                >
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
