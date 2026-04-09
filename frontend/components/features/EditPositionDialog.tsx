/**
 * 编辑持仓对话框组件 (Edit Position Dialog)
 *
 * 职责：
 * - 提供用户界面以修改持仓数量和成本价
 * - 表单验证和数据提交
 * - 实时计算总成本
 *
 * 组件结构：
 * - EditPositionDialog: 完整的对话框组件
 * - EditPositionButton: 便捷的触发按钮（支持两种变体）
 *
 * 使用场景：
 * - 用户买入/卖出后调整持仓数量
 * - 修正错误的成本价输入
 * - 分批建仓后更新平均成本
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
import { Pencil, Save, X } from "lucide-react";
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

    return (
        <Dialog open={isOpen} onOpenChange={setOpen}>
            <DialogContent className="sm:max-w-md bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-2xl">
                <DialogHeader>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-600/10 flex items-center justify-center border border-blue-600/20">
                            <Pencil className="h-4 w-4 text-blue-600" />
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
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* 错误提示 */}
                    {error && (
                        <div className="p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg">
                            <p className="text-xs text-rose-600 dark:text-rose-400 font-medium">{error}</p>
                        </div>
                    )}

                    {/* 持仓数量输入 */}
                    <div className="space-y-2">
                        <Label htmlFor="quantity" className="text-xs font-bold text-slate-600 dark:text-slate-400">
                            持仓数量 (Shares)
                        </Label>
                        <Input
                            id="quantity"
                            type="number"
                            step="0.01"
                            value={editedQuantity}
                            onChange={(e) => setEditedQuantity(e.target.value)}
                            className="h-10 font-mono tabular-nums"
                            placeholder="0"
                        />
                    </div>

                    {/* 持仓均价输入 */}
                    <div className="space-y-2">
                        <Label htmlFor="avgCost" className="text-xs font-bold text-slate-600 dark:text-slate-400">
                            持仓均价 (Cost Basis)
                        </Label>
                        <Input
                            id="avgCost"
                            type="number"
                            step="0.01"
                            value={editedAvgCost}
                            onChange={(e) => setEditedAvgCost(e.target.value)}
                            className="h-10 font-mono tabular-nums"
                            placeholder="0.00"
                        />
                    </div>

                    {/* 总成本预览 */}
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">总成本</span>
                            <span className="text-sm font-black text-slate-900 dark:text-white tabular-nums">
                                ${calculateMarketValue().toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                        </div>
                    </div>
                </div>

                <DialogFooter className="gap-2 sm:gap-0">
                    {/* 取消按钮 */}
                    <Button
                        variant="outline"
                        onClick={() => setOpen(false)}
                        className="h-10 font-bold border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
                        disabled={loading}
                    >
                        <X className="h-4 w-4 mr-1.5" />
                        取消
                    </Button>
                    {/* 保存按钮 */}
                    <Button
                        onClick={handleSubmit}
                        className="h-10 bg-blue-600 hover:bg-blue-700 text-white font-bold"
                        disabled={loading}
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
