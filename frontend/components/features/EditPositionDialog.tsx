/**
 * 编辑持仓对话框组件 (Edit Position Dialog)
 *
 * 职责：
 * - 提供用户界面以修改持仓数量和成本价
 * - 表单验证和数据提交
 * - 实时计算总成本
 * - 支持一键清空持仓（不再持有）
 *
 * 组件结构：
 * - EditPositionDialog: 完整的对话框组件
 * - EditPositionButton: 便捷的触发按钮（支持两种变体）
 *
 * 使用场景：
 * - 用户买入/卖出后调整持仓数量
 * - 修正错误的成本价输入
 * - 分批建仓后更新平均成本
 * - 清仓后删除持仓记录
 */
"use client";

import React, { useState, useEffect } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PortfolioItem } from "@/types";
import { Pencil, Save, X, Trash2, AlertTriangle } from "lucide-react";
import clsx from "clsx";

/**
 * EditPositionDialog Props 接口
 *
 * @property ticker - 股票代码（用于 API 请求和显示）
 * @property quantity - 当前持仓数量（初始值）
 * @property avg_cost - 当前持仓均价（初始值）
 * @property open - 对话框打开状态（受控模式）
 * @property onOpenChange - 打开状态变化回调（受控模式）
 * @property onSuccess - 保存成功后的回调（用于刷新父组件数据）
 */
interface EditPositionDialogProps {
    ticker: string;
    quantity: number;
    avg_cost: number;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    onSuccess?: () => void;
}

/**
 * 编辑持仓对话框主组件
 *
 * 功能特性：
 * - 支持受控和非受控两种模式
 * - 打开时自动重置为当前值
 * - 表单验证（数量 > 0, 成本 > 0）
 * - 实时计算总成本
 * - 错误提示
 */
export function EditPositionDialog({
    ticker,
    quantity,
    avg_cost,
    open = false,
    onOpenChange,
    onSuccess,
}: EditPositionDialogProps) {
    // 内部状态（非受控模式）
    const [internalOpen, setInternalOpen] = useState(false);
    // 编辑中的表单值
    const [editedQuantity, setEditedQuantity] = useState(quantity.toString());
    const [editedAvgCost, setEditedAvgCost] = useState(avg_cost.toString());
    // 加载和错误状态
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    // 删除确认对话框状态
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleting, setDeleting] = useState(false);

    // 确定使用受控还是非受控模式
    const isOpen = onOpenChange !== undefined ? open : internalOpen;
    const setOpen = onOpenChange || setInternalOpen;

    // 当对话框打开时，重置表单值为当前值
    useEffect(() => {
        if (isOpen) {
            setEditedQuantity(quantity.toString());
            setEditedAvgCost(avg_cost.toString());
            setError(null);
        }
    }, [isOpen, quantity, avg_cost]);

    /**
     * 计算总成本
     * @returns 持仓数量 × 持仓均价
     */
    const calculateMarketValue = () => {
        const qty = parseFloat(editedQuantity) || 0;
        const price = parseFloat(editedAvgCost) || 0;
        return qty * price;
    };

    /**
     * 提交表单处理函数
     *
     * 流程：
     * 1. 验证输入值（必须为正数）
     * 2. 发送 PATCH 请求到后端 API
     * 3. 成功后关闭对话框并触发回调
     * 4. 失败时显示错误信息
     */
    const handleSubmit = async () => {
        setLoading(true);
        setError(null);

        const qty = parseFloat(editedQuantity);
        const cost = parseFloat(editedAvgCost);

        // 验证持仓数量
        if (isNaN(qty) || qty <= 0) {
            setError("请输入有效的持仓数量（必须大于 0）");
            setLoading(false);
            return;
        }

        // 验证持仓均价
        if (isNaN(cost) || cost <= 0) {
            setError("请输入有效的持仓均价（必须大于 0）");
            setLoading(false);
            return;
        }

        try {
            const response = await fetch(`/api/v1/portfolio/${ticker}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
                body: JSON.stringify({
                    quantity: qty,
                    avg_cost: cost,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "更新失败");
            }

            setOpen(false);
            onSuccess?.();
        } catch (err) {
            setError(err instanceof Error ? err.message : "更新失败，请重试");
        } finally {
            setLoading(false);
        }
    };

    /**
     * 删除持仓（不再持有）
     */
    const handleDelete = async () => {
        setDeleting(true);
        setError(null);

        try {
            const response = await fetch(`/api/v1/portfolio/${ticker}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("token")}`,
                },
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "删除失败");
            }

            setShowDeleteConfirm(false);
            setOpen(false);
            onSuccess?.();
        } catch (err) {
            setError(err instanceof Error ? err.message : "删除失败，请重试");
            setShowDeleteConfirm(false);
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={setOpen}>
            <DialogContent className="sm:max-w-md bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-linear-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/20">
                                <Pencil className="h-4 w-4 text-white" />
                            </div>
                            <div>
                                <DialogTitle className="font-black text-base text-slate-900 dark:text-white">
                                    编辑持仓
                                </DialogTitle>
                                <DialogDescription className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                                    {ticker}
                                </DialogDescription>
                            </div>
                        </div>
                    </div>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    {/* 错误提示 */}
                    {error && (
                        <div className="p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400 mt-0.5 shrink-0" />
                            <p className="text-xs text-rose-600 dark:text-rose-400 font-medium">{error}</p>
                        </div>
                    )}

                    {/* 持仓数量输入 */}
                    <div className="space-y-2">
                        <Label htmlFor="quantity" className="text-xs font-bold text-slate-600 dark:text-slate-400 flex items-center gap-2">
                            <span>持仓数量</span>
                            <span className="text-[10px] font-normal text-slate-400">(Shares)</span>
                        </Label>
                        <div className="relative">
                            <Input
                                id="quantity"
                                type="number"
                                step="0.01"
                                value={editedQuantity}
                                onChange={(e) => setEditedQuantity(e.target.value)}
                                className="h-11 font-mono tabular-nums pr-12 border-slate-200 dark:border-slate-700 focus:border-blue-500 focus:ring-blue-500"
                                placeholder="0"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
                                股
                            </span>
                        </div>
                    </div>

                    {/* 持仓均价输入 */}
                    <div className="space-y-2">
                        <Label htmlFor="avgCost" className="text-xs font-bold text-slate-600 dark:text-slate-400 flex items-center gap-2">
                            <span>持仓均价</span>
                            <span className="text-[10px] font-normal text-slate-400">(Cost Basis)</span>
                        </Label>
                        <div className="relative">
                            <Input
                                id="avgCost"
                                type="number"
                                step="0.01"
                                value={editedAvgCost}
                                onChange={(e) => setEditedAvgCost(e.target.value)}
                                className="h-11 font-mono tabular-nums pr-12 border-slate-200 dark:border-slate-700 focus:border-blue-500 focus:ring-blue-500"
                                placeholder="0.00"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
                                $
                            </span>
                        </div>
                    </div>

                    {/* 总成本预览 */}
                    <div className="p-4 bg-linear-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-800/30 rounded-xl border border-slate-200 dark:border-slate-700">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">总成本</span>
                            <span className="text-lg font-black text-slate-900 dark:text-white tabular-nums">
                                ${calculateMarketValue().toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                        </div>
                    </div>

                    {/* 分割线 */}
                    <div className="h-px bg-slate-100 dark:bg-slate-800" />

                    {/* 不再持有按钮 */}
                    {!showDeleteConfirm ? (
                        <button
                            type="button"
                            onClick={() => setShowDeleteConfirm(true)}
                            className="w-full h-10 rounded-xl border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-all duration-200 flex items-center justify-center gap-2 font-bold text-sm"
                        >
                            <Trash2 className="h-4 w-4" />
                            不再持有此股票
                        </button>
                    ) : (
                        <div className="p-3 bg-rose-50 dark:bg-rose-900/20 rounded-xl border border-rose-200 dark:border-rose-800 space-y-3">
                            <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400">
                                <AlertTriangle className="h-4 w-4" />
                                <span className="text-sm font-bold">确认删除持仓？</span>
                            </div>
                            <p className="text-xs text-rose-600 dark:text-rose-400">
                                此操作将永久删除 <span className="font-mono font-black">{ticker}</span> 的持仓记录
                            </p>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => setShowDeleteConfirm(false)}
                                    disabled={deleting}
                                    className="flex-1 h-9 rounded-lg border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/30 transition-all font-bold text-sm disabled:opacity-50"
                                >
                                    取消
                                </button>
                                <button
                                    type="button"
                                    onClick={handleDelete}
                                    disabled={deleting}
                                    className="flex-1 h-9 rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition-all font-bold text-sm disabled:opacity-50 flex items-center justify-center gap-1.5"
                                >
                                    <Trash2 className="h-3.5 w-3.5" />
                                    {deleting ? "删除中..." : "确认删除"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter className="gap-2 sm:gap-0 border-t border-slate-100 dark:border-slate-800 pt-4">
                    {/* 取消按钮 */}
                    <Button
                        variant="outline"
                        onClick={() => {
                            setShowDeleteConfirm(false);
                            setOpen(false);
                        }}
                        className="h-10 font-bold border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
                        disabled={loading || deleting}
                    >
                        <X className="h-4 w-4 mr-1.5" />
                        取消
                    </Button>
                    {/* 保存按钮 */}
                    <Button
                        onClick={handleSubmit}
                        className="h-10 bg-linear-to-br from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-bold shadow-lg shadow-blue-500/25"
                        disabled={loading || deleting}
                    >
                        <Save className="h-4 w-4 mr-1.5" />
                        {loading ? "保存中..." : "保存"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

/**
 * EditPositionButton Props 接口
 *
 * @property ticker - 股票代码
 * @property quantity - 当前持仓数量
 * @property avg_cost - 当前持仓均价
 * @property onSuccess - 保存成功回调
 * @property variant - 按钮变体（"inline" | "full"）
 */
interface EditPositionButtonProps {
    ticker: string;
    quantity: number;
    avg_cost: number;
    onSuccess?: () => void;
    variant?: "inline" | "full";
}

/**
 * 编辑按钮组件（带内置对话框）
 *
 * 两种变体：
 * - inline: 紧凑版本，仅显示铅笔图标，适合嵌入行内
 * - full: 完整版本，显示图标和文字，适合独立放置
 *
 * 使用示例：
 * ```tsx
 * // 行内模式
 * <EditPositionButton ticker="AAPL" quantity={10} avg_cost={150.5} variant="inline" />
 *
 * // 完整模式
 * <EditPositionButton ticker="AAPL" quantity={10} avg_cost={150.5} variant="full" />
 * ```
 */
export function EditPositionButton({
    ticker,
    quantity,
    avg_cost,
    onSuccess,
    variant = "inline",
}: EditPositionButtonProps) {
    const [open, setOpen] = useState(false);

    if (variant === "inline") {
        return (
            <>
                {/* 紧凑编辑按钮 - 仅图标 */}
                <button
                    type="button"
                    onClick={() => setOpen(true)}
                    className="p-1 -my-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                    title="编辑持仓"
                >
                    <Pencil className="h-3.5 w-3.5" />
                </button>
                <EditPositionDialog
                    ticker={ticker}
                    quantity={quantity}
                    avg_cost={avg_cost}
                    open={open}
                    onOpenChange={setOpen}
                    onSuccess={onSuccess}
                />
            </>
        );
    }

    return (
        <>
            {/* 完整编辑按钮 - 图标 + 文字 */}
            <Button
                variant="outline"
                size="sm"
                onClick={() => setOpen(true)}
                className="gap-2 h-9 font-bold"
            >
                <Pencil className="h-4 w-4" />
                编辑持仓
            </Button>
            <EditPositionDialog
                ticker={ticker}
                quantity={quantity}
                avg_cost={avg_cost}
                open={open}
                onOpenChange={setOpen}
                onSuccess={onSuccess}
            />
        </>
    );
}
