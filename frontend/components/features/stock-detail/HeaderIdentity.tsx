/**
 * 股票身份头组件 (Header Identity)
 *
 * 职责：
 * - 展示股票名称、 ticker、实时价格、涨跌幅
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
import { RefreshCw, ChevronLeft, Pencil } from "lucide-react";
import { HeaderIdentityProps } from "./types";
import { EditPositionDialog } from "@/components/features/EditPositionDialog";

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
    // 编辑对话框打开状态
    const [editDialogOpen, setEditDialogOpen] = useState(false);

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
                    <div className="hidden sm:flex flex-col items-end">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">最新涨跌</span>
                        <span className={clsx(
                            "text-lg font-black tabular-nums",
                            (selectedItem.change_percent || 0) >= 0 ? "text-emerald-600" : "text-rose-600"
                        )}>
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

            {/* 持仓信息区域（仅当持有时显示）
             * 优化：采用单行水平布局，减少垂直空间占用
             * 从原来的 2 行网格改为 1 行 flex 布局，高度减少约 40%
             */}
            {selectedItem.quantity > 0 && (
                <div className="flex items-center gap-6 mt-2 pt-2.5 border-t border-slate-50 dark:border-slate-800/50">
                    {/* 持有仓位（带编辑按钮） */}
                    <div className="flex items-center gap-2">
                        <div className="flex flex-col">
                            <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">持有仓位</span>
                            <span className="text-sm font-bold text-slate-700 dark:text-slate-300 tabular-nums">
                                {selectedItem.quantity} Shares
                            </span>
                        </div>
                        {/* 编辑按钮 - 铅笔图标 */}
                        <button
                            type="button"
                            onClick={() => setEditDialogOpen(true)}
                            className="p-1 -mt-0.5 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                            title="编辑持仓"
                        >
                            <Pencil className="h-3.5 w-3.5" />
                        </button>
                    </div>

                    {/* 持仓均价 */}
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">持仓均价</span>
                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300 tabular-nums">
                            ${selectedItem.avg_cost.toFixed(2)}
                        </span>
                    </div>

                    {/* 账面盈亏（金额 + 百分比） */}
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider">账面盈亏</span>
                        <div className="flex items-center gap-1.5">
                            {/* 盈亏金额 */}
                            <span className={clsx(
                                "text-sm font-bold tabular-nums",
                                selectedItem.unrealized_pl >= 0 ? "text-emerald-600" : "text-rose-600"
                            )}>
                                {selectedItem.unrealized_pl >= 0 ? "+" : ""}${selectedItem.unrealized_pl.toFixed(2)}
                            </span>
                            {/* 盈亏百分比（带背景色） */}
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
                </div>
            )}

            {/* 编辑持仓对话框 */}
            <EditPositionDialog
                ticker={selectedItem.ticker}
                quantity={selectedItem.quantity}
                avg_cost={selectedItem.avg_cost}
                open={editDialogOpen}
                onOpenChange={setEditDialogOpen}
                onSuccess={onRefresh}
            />

            {/* Tab 标签导航（标的信息 / AI 分析） */}
            {onTabChange && (
                <div className="flex border-b border-slate-100 dark:border-zinc-800 mt-1">
                    {tabs.map(({ key, label }) => (
                        <button
                            key={key}
                            type="button"
                            onClick={() => onTabChange(key)}
                            className={clsx(
                                "relative px-4 py-2.5 text-sm font-semibold transition-colors duration-200",
                                activeTab === key
                                    ? "text-slate-900 dark:text-white"
                                    : "text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
                            )}
                        >
                            {label}
                            {/* 激活态下划线 */}
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
