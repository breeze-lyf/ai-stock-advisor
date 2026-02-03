"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Zap, RefreshCw } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { PortfolioItem } from "@/types";
import { refreshStock } from "@/lib/api";
import { useState } from "react";

interface StockDetailProps {
    selectedItem: PortfolioItem | null;
    onAnalyze: () => void;
    onRefresh: () => void;
    analyzing: boolean;
    aiData: {
        technical_analysis: string;
        fundamental_news: string;
        action_advice: string;
    } | null;
}

export function StockDetail({
    selectedItem,
    onAnalyze,
    onRefresh,
    analyzing,
    aiData,
}: StockDetailProps) {
    const [refreshing, setRefreshing] = useState(false);

    if (!selectedItem) {
        return (
            <div className="col-span-9 bg-slate-50 dark:bg-slate-950 p-6 flex flex-col items-center justify-center h-full text-slate-300 gap-2 overflow-y-auto custom-scrollbar">
                <Zap className="h-12 w-12 opacity-10" />
                <p className="text-sm font-medium">请从左侧选择一个代码查看详情</p>
            </div>
        );
    }

    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            await refreshStock(selectedItem.ticker);
            await onRefresh();
        } catch (err) {
            console.error("Refresh failed", err);
        } finally {
            setRefreshing(false);
        }
    };

    return (
        <div className="col-span-9 bg-slate-50 dark:bg-slate-950 p-6 flex flex-col gap-6 overflow-y-auto h-full custom-scrollbar">
            <div className="flex justify-between items-start">
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-4">
                        <h2 className="text-4xl font-black tracking-tight text-slate-800 dark:text-slate-100 italic">
                            {selectedItem.ticker}
                        </h2>
                        <Button
                            variant="ghost"
                            size="icon"
                            className={clsx(
                                "h-10 w-10 transition-all duration-300",
                                refreshing
                                    ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20"
                                    : "text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-slate-800"
                            )}
                            onClick={handleRefresh}
                            disabled={refreshing}
                            title="刷新数据"
                        >
                            <RefreshCw className={clsx("h-6 w-6", refreshing && "animate-spin")} />
                        </Button>
                    </div>

                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                        <p className="text-lg font-mono text-slate-500">
                            Price:{" "}
                            <span className="text-slate-800 dark:text-slate-200 font-bold">
                                ${selectedItem.current_price.toFixed(2)}
                            </span>
                        </p>
                        <span className="text-slate-300">|</span>
                        <p className="text-lg font-mono text-slate-500">
                            Value:{" "}
                            <span className="text-blue-600 font-bold">
                                ${selectedItem.market_value.toFixed(2)}
                            </span>
                        </p>
                        <span className="text-slate-300">|</span>
                        <p className="text-sm font-mono text-slate-500">
                            Size:{" "}
                            <span className="text-slate-800 dark:text-slate-200 font-bold">
                                {selectedItem.quantity}
                            </span>
                        </p>
                        <span className="text-slate-300">|</span>
                        <p className="text-sm font-mono text-slate-500">
                            Avg Cost:{" "}
                            <span className="text-slate-800 dark:text-slate-200 font-bold">
                                ${selectedItem.avg_cost.toFixed(2)}
                            </span>
                        </p>
                    </div>
                </div>
                <Button
                    onClick={onAnalyze}
                    disabled={analyzing}
                    size="lg"
                    className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 px-8 py-6 text-lg font-bold"
                >
                    <Zap className={clsx("mr-2 h-5 w-5", analyzing && "animate-pulse")} />
                    {analyzing ? "AI 正在分析深度数据..." : "AI 深度分析"}
                </Button>
            </div>

            <div className="grid gap-6">
                {/* 1. Fundamentals */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800">
                    <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20">
                        <CardTitle className="text-sm font-bold flex items-center gap-2 uppercase tracking-wider text-slate-600 dark:text-slate-400">
                            基本面数据 (Fundamentals)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                        {/* Fundamental Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                            {[
                                {
                                    label: "Market Cap",
                                    value: selectedItem.market_cap
                                        ? (selectedItem.market_cap / 1e9).toFixed(1) + "B"
                                        : "-",
                                },
                                { label: "PE Ratio", value: selectedItem.pe_ratio?.toFixed(2) || "-" },
                                { label: "Forward PE", value: selectedItem.forward_pe?.toFixed(2) || "-" },
                                { label: "EPS", value: selectedItem.eps?.toFixed(2) || "-" },
                                { label: "Beta", value: selectedItem.beta?.toFixed(2) || "-" },
                                {
                                    label: "Div Yield",
                                    value: selectedItem.dividend_yield
                                        ? (selectedItem.dividend_yield * 100).toFixed(2) + "%"
                                        : "-",
                                },
                                {
                                    label: "52W High",
                                    value: selectedItem.fifty_two_week_high?.toFixed(2) || "-",
                                },
                                {
                                    label: "52W Low",
                                    value: selectedItem.fifty_two_week_low?.toFixed(2) || "-",
                                },
                                { label: "Sector", value: selectedItem.sector || "-" },
                                { label: "Industry", value: selectedItem.industry || "-" },
                            ].map((stat) => (
                                <div
                                    key={stat.label}
                                    className="flex flex-col p-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded shadow-sm"
                                >
                                    <span className="text-[9px] text-slate-400 font-bold uppercase truncate">
                                        {stat.label}
                                    </span>
                                    <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 truncate">
                                        {stat.value}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {aiData && (
                            <div className="prose dark:prose-invert text-sm max-w-none leading-relaxed border-t pt-4">
                                <ReactMarkdown>{aiData.fundamental_news}</ReactMarkdown>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* 2. Technical Indicators */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800 overflow-hidden">
                    <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20 flex flex-row items-center justify-between">
                        <CardTitle className="text-sm font-bold flex items-center gap-2 uppercase tracking-wider text-slate-600 dark:text-slate-400">
                            技术指标 (Technical Indicators)
                        </CardTitle>
                        {selectedItem.last_updated && (
                            <div className="text-[10px] text-slate-400 font-mono">
                                数据时间:{" "}
                                {formatDistanceToNow(new Date(selectedItem.last_updated + "Z"), {
                                    addSuffix: true,
                                    locale: zhCN,
                                })}
                            </div>
                        )}
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                        {/* Technical Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                            {[
                                { label: "RSI (14)", value: selectedItem.rsi_14?.toFixed(2) || "-" },
                                { label: "MA 20", value: selectedItem.ma_20?.toFixed(2) || "-" },
                                { label: "MA 50", value: selectedItem.ma_50?.toFixed(2) || "-" },
                                { label: "MA 200", value: selectedItem.ma_200?.toFixed(2) || "-" },
                                { label: "MACD", value: selectedItem.macd_val?.toFixed(2) || "-" },
                                { label: "MACD Hist", value: selectedItem.macd_hist?.toFixed(2) || "-" },
                                { label: "ATR (14)", value: selectedItem.atr_14?.toFixed(2) || "-" },
                                { label: "BB Upper", value: selectedItem.bb_upper?.toFixed(2) || "-" },
                                { label: "BB Lower", value: selectedItem.bb_lower?.toFixed(2) || "-" },
                                { label: "KDJ - K", value: selectedItem.k_line?.toFixed(1) || "-" },
                                { label: "KDJ - D", value: selectedItem.d_line?.toFixed(1) || "-" },
                                { label: "Vol Ratio", value: selectedItem.volume_ratio?.toFixed(2) || "-" },
                            ].map((stat) => (
                                <div
                                    key={stat.label}
                                    className="flex flex-col p-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded shadow-sm"
                                >
                                    <span className="text-[9px] text-slate-400 font-bold uppercase truncate">
                                        {stat.label}
                                    </span>
                                    <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 truncate">
                                        {stat.value}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {aiData && (
                            <div className="prose dark:prose-invert text-sm max-w-none leading-relaxed border-t pt-4">
                                <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* 3. AI Advice */}
                <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-900/5 shadow-md shadow-blue-500/5">
                    <CardHeader className="pb-2 border-b border-blue-100 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-900/20">
                        <CardTitle className="text-base font-bold text-blue-700 dark:text-blue-400 flex items-center gap-2">
                            AI 给出的操作建议 (Actionable Advice)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 pb-6">
                        {aiData ? (
                            <div className="prose dark:prose-invert text-base max-w-none font-medium text-blue-900 dark:text-blue-100 leading-relaxed bg-white/50 dark:bg-slate-900/50 p-4 rounded-lg border border-blue-50 dark:border-blue-900/30">
                                <ReactMarkdown>{aiData.action_advice}</ReactMarkdown>
                            </div>
                        ) : (
                            <div className="text-blue-300/50 italic text-sm py-4 italic">
                                等待分析中...
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
