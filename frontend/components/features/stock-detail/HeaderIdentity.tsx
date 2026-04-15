/**
 * 股票身份头组件 (Header Identity)
 *
 * 职责：
 * - 展示股票名称、ticker、实时价格、涨跌幅
 * - 展示用户持仓信息（数量、成本、盈亏）
 * - 提供刷新行情和编辑持仓的快捷操作
 * - 页面滚动时自动淡出，将空间让给粘性顶栏
 *
 * 设计特点：
 * - 响应式布局（移动端/桌面端自适应）
 * - 持仓信息单行紧凑布局，减少垂直空间占用
 * - 编辑按钮集成在持仓数量旁，便于发现和操作
 *
 * 使用场景：
 * - 个股详情页顶部
 * - 投资组合详情页
 */
"use client";

import React, { useState } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/button";
import { RefreshCw, ChevronLeft, Pencil, Save, X, Trash2 } from "lucide-react";
import { HeaderIdentityProps } from "./types";

/**
 * HeaderIdentity 组件主函数
 *
 * @param selectedItem - 当前选中的股票/持仓数据
 * @param isScrolled - 页面是否已滚动（用于控制淡出）
 * @param refreshing - 是否正在刷新数据
 * @param onRefresh - 刷新行情回调
 * @param onBack - 返回按钮回调（移动端）
 * @param activeTab - 当前激活的标签页
 * @param onTabChange - 标签页切换回调
 */
export const HeaderIdentity = React.memo(function HeaderIdentity({
    selectedItem,
    isScrolled,
    refreshing,
    onRefresh,
    onBack,
    activeTab = "info",
    onTabChange,
}: HeaderIdentityProps) {
    // 内联编辑状态
    const [isEditing, setIsEditing] = useState(false);
    const [editedQuantity, setEditedQuantity] = useState("");
    const [editedAvgCost, setEditedAvgCost] = useState("");
    const [editLoading, setEditLoading] = useState(false);
    const [editDeleting, setEditDeleting] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);

    const handleStartEdit = () => {
        setEditedQuantity(selectedItem.quantity > 0 ? String(selectedItem.quantity) : "");
        setEditedAvgCost(selectedItem.avg_cost > 0 ? String(selectedItem.avg_cost) : "");
        setEditError(null);
        setIsEditing(true);
    };

    const handleCancelEdit = () => {
        setIsEditing(false);
        setEditError(null);
    };

    const handleSaveEdit = async () => {
        const qty = parseFloat(editedQuantity);
        const cost = parseFloat(editedAvgCost);
        if (isNaN(qty) || qty <= 0) { setEditError("持仓数量必须大于 0"); return; }
        if (isNaN(cost) || cost <= 0) { setEditError("持仓均价必须大于 0"); return; }
        setEditLoading(true);
        setEditError(null);
        const isNewPosition = selectedItem.quantity <= 0;
        try {
            const response = isNewPosition
                ? await fetch(`/api/v1/portfolio/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${localStorage.getItem("token")}`,
                    },
                    body: JSON.stringify({ ticker: selectedItem.ticker, quantity: qty, avg_cost: cost }),
                })
                : await fetch(`/api/v1/portfolio/${selectedItem.ticker}`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${localStorage.getItem("token")}`,
                    },
                    body: JSON.stringify({ quantity: qty, avg_cost: cost }),
                });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "更新失败");
            }
            setIsEditing(false);
            onRefresh?.();
        } catch (err) {
            setEditError(err instanceof Error ? err.message : "更新失败，请重试");
        } finally {
            setEditLoading(false);
        }
    };

    const handleClosePosition = async () => {
        setEditDeleting(true);
        setEditError(null);
        try {
            const response = await fetch(`/api/v1/portfolio/${selectedItem.ticker}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
            });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "删除失败");
            }
            setIsEditing(false);
            onRefresh?.();
        } catch (err) {
            setEditError(err instanceof Error ? err.message : "删除失败，请重试");
        } finally {
            setEditDeleting(false);
        }
    };

    // 标签页定义
    const tabs = [
        { key: "info" as const, label: "标的信息" },
        { key: "analysis" as const, label: "AI 分析" },
    ];

    return (
        <div className={clsx(
            "flex flex-col gap-2 transition-all duration-500",
            isScrolled && "opacity-0 pointer-events-none"
        )}>
            {/* 主标题区域 */}
            <div className="flex flex-col sm:flex-row justify-between sm:items-end gap-3 sm:gap-4">
                {/* 左侧：返回按钮 + 股票名称 */}
                <div className="flex items-start gap-2">
                    {/* 返回按钮（仅移动端显示） */}
                    {onBack && (
                        <button
                            onClick={onBack}
                            title="返回"
                            aria-label="返回"
                            className="lg:hidden mt-1 p-1 -ml-1 rounded-full text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
                        >
                            <ChevronLeft className="h-7 w-7" />
                        </button>
                    )}

                    {/* 股票名称和代码 */}
                    <div className="flex flex-col">
                        <div className="flex items-center gap-3">
                            <h1 className="text-3xl md:text-4xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                                {selectedItem.name || selectedItem.ticker}
                            </h1>
                            {/* 刷新按钮 */}
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
                        {/* 股票代码（当有名称时显示） */}
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mt-2">
                            {selectedItem.name ? selectedItem.ticker : "全维度财务声誉分析"}
                        </p>
                    </div>
                </div>

                {/* 右侧：最新涨跌 + 实时价格 */}
                <div className="flex items-center gap-6 sm:gap-10">
                    {/* 最新涨跌（桌面端显示） */}
                    <div className="hidden sm:flex flex-col items-end gap-2">
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">最新涨跌</span>
                            <span className={clsx(
                                "text-lg font-black tabular-nums",
                                (selectedItem.change_percent || 0) >= 0 ? "text-emerald-600" : "text-rose-600"
                            )}>
                                {(selectedItem.change_percent || 0) >= 0 ? "+" : ""}{selectedItem.change_percent?.toFixed(2)}%
                            </span>
                        </div>
                    </div>

                    {/* 实时价格 */}
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-3xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                            ${selectedItem.current_price.toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>

            {/* 持仓信息 + Tab 导航行：持仓在左，Tab 靠右，始终渲染（Tab 无持仓时也需显示） */}
            <div className="flex items-center flex-wrap gap-x-6 gap-y-2 mt-2 pb-1.5 border-b border-slate-100 dark:border-slate-800/50">
                {/* 持仓信息（有持仓才显示） */}
                {selectedItem.quantity > 0 ? (
                    <>
                        {isEditing ? (
                            /* 内联编辑模式（有持仓） */
                            <>
                                {editError && (
                                    <span className="w-full text-xs text-rose-600 font-medium -mb-1">{editError}</span>
                                )}
                                <div className="flex items-center gap-1.5">
                                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider whitespace-nowrap">持有仓位</span>
                                    <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        title="持仓数量"
                                        placeholder="0"
                                        value={editedQuantity}
                                        onChange={(e) => setEditedQuantity(e.target.value)}
                                        className="w-20 h-7 px-2 text-sm font-mono tabular-nums border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 dark:text-slate-100"
                                    />
                                    <span className="text-[10px] text-slate-400 font-bold">股</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider whitespace-nowrap">持仓均价</span>
                                    <span className="text-[10px] text-slate-400 font-bold">$</span>
                                    <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        title="持仓均价"
                                        placeholder="0.00"
                                        value={editedAvgCost}
                                        onChange={(e) => setEditedAvgCost(e.target.value)}
                                        className="w-24 h-7 px-2 text-sm font-mono tabular-nums border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 dark:text-slate-100"
                                    />
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <button
                                        type="button"
                                        onClick={handleSaveEdit}
                                        disabled={editLoading || editDeleting}
                                        className="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                                    >
                                        <Save className="h-3 w-3" />
                                        {editLoading ? "保存中..." : "保存"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleCancelEdit}
                                        disabled={editLoading || editDeleting}
                                        className="h-7 px-2 rounded-md border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                                    >
                                        <X className="h-3 w-3" />
                                        取消
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleClosePosition}
                                        disabled={editLoading || editDeleting}
                                        className="h-7 px-2.5 rounded-md border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                                    >
                                        <Trash2 className="h-3 w-3" />
                                        {editDeleting ? "平仓中..." : "平仓"}
                                    </button>
                                </div>
                            </>
                        ) : (
                            /* 展示模式 */
                            <>
                                <div className="flex items-center gap-2">
                                    <div className="flex flex-col">
                                        <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">持有仓位</span>
                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300 tabular-nums">
                                            {selectedItem.quantity} Shares
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={handleStartEdit}
                                        className="p-1 -mt-0.5 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                                        title="编辑持仓"
                                    >
                                        <Pencil className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">持仓均价</span>
                                    <span className="text-sm font-bold text-slate-700 dark:text-slate-300 tabular-nums">
                                        ${selectedItem.avg_cost.toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">账面盈亏</span>
                                    <div className="flex items-center gap-1.5">
                                        <span className={clsx(
                                            "text-sm font-bold tabular-nums",
                                            selectedItem.unrealized_pl >= 0 ? "text-emerald-600" : "text-rose-600"
                                        )}>
                                            {selectedItem.unrealized_pl >= 0 ? "+" : ""}${selectedItem.unrealized_pl.toFixed(2)}
                                        </span>
                                        <span className={clsx(
                                            "text-[9px] font-black px-1 py-0.5 rounded-md",
                                            selectedItem.pl_percent >= 0
                                                ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-600/10 dark:text-emerald-400"
                                                : "bg-rose-50 text-rose-600 dark:bg-rose-600/10 dark:text-rose-400"
                                        )}>
                                            {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                                        </span>
                                    </div>
                                </div>
                            </>
                        )}
                    </>
                ) : (
                    /* 空仓时：编辑中显示输入框，否则显示设置持仓按钮 */
                    isEditing ? (
                        <>
                            {editError && (
                                <span className="w-full text-xs text-rose-600 font-medium -mb-1">{editError}</span>
                            )}
                            <div className="flex items-center gap-1.5">
                                <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider whitespace-nowrap">持有仓位</span>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    title="持仓数量"
                                    placeholder="0"
                                    value={editedQuantity}
                                    onChange={(e) => setEditedQuantity(e.target.value)}
                                    className="w-20 h-7 px-2 text-sm font-mono tabular-nums border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 dark:text-slate-100"
                                />
                                <span className="text-[10px] text-slate-400 font-bold">股</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider whitespace-nowrap">持仓均价</span>
                                <span className="text-[10px] text-slate-400 font-bold">$</span>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    title="持仓均价"
                                    placeholder="0.00"
                                    value={editedAvgCost}
                                    onChange={(e) => setEditedAvgCost(e.target.value)}
                                    className="w-24 h-7 px-2 text-sm font-mono tabular-nums border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-md focus:outline-none focus:border-blue-500 text-slate-800 dark:text-slate-100"
                                />
                            </div>
                            <div className="flex items-center gap-1.5">
                                <button
                                    type="button"
                                    onClick={handleSaveEdit}
                                    disabled={editLoading}
                                    className="h-7 px-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                                >
                                    <Save className="h-3 w-3" />
                                    {editLoading ? "保存中..." : "保存"}
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCancelEdit}
                                    disabled={editLoading}
                                    className="h-7 px-2 rounded-md border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                                >
                                    <X className="h-3 w-3" />
                                    取消
                                </button>
                            </div>
                        </>
                    ) : (
                        <button
                            type="button"
                            onClick={handleStartEdit}
                            className="flex items-center gap-1.5 h-7 px-3 rounded-md border border-dashed border-slate-300 dark:border-slate-600 text-slate-400 dark:text-slate-500 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-bold transition-colors"
                        >
                            <Pencil className="h-3 w-3" />
                            设置持仓
                        </button>
                    )
                )}

                {/* Tab 标签导航 — 靠右，与持仓信息同行 */}
                {onTabChange && (
                    <div className="ml-auto flex items-center">
                        {tabs.map(({ key, label }) => (
                            <button
                                key={key}
                                type="button"
                                onClick={() => onTabChange(key)}
                                className={clsx(
                                    "relative px-3 py-1.5 text-xs font-semibold transition-colors duration-200",
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
        </div>
    );
});
