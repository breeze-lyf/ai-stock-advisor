"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Zap, RefreshCw, Activity, Newspaper, TrendingUp, BarChart3, Clock, AlertCircle, Target, ShieldAlert, ShieldCheck } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { zhCN } from "date-fns/locale";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { PortfolioItem } from "@/types";
import { refreshStock, fetchStockHistory } from "@/lib/api";
import { StockNewsList } from "./StockNewsList";
import { StockChart } from "./StockChart";

interface StockDetailProps {
    selectedItem: PortfolioItem | null;
    onAnalyze: (force?: boolean) => void;
    onRefresh: () => void;
    analyzing: boolean;
    aiData: {
        sentiment_score?: number;
        summary_status?: string;
        risk_level?: string;
        technical_analysis: string;
        fundamental_news: string;
        action_advice: string;
        immediate_action?: string;
        target_price?: number;
        stop_loss_price?: number;
        entry_zone?: string;
        entry_price_low?: number;
        entry_price_high?: number;
        rr_ratio?: string;
        investment_horizon?: string;
        confidence_level?: number;
        is_cached?: boolean;
        created_at?: string;
        model_used?: string;
    } | null;
    news?: any[];
}

export function StockDetail({
    selectedItem,
    onAnalyze,
    onRefresh,
    analyzing,
    aiData,
    news = []
}: StockDetailProps) {
    const [refreshing, setRefreshing] = useState(false);
    const [historyData, setHistoryData] = useState<any[]>([]);

    useEffect(() => {
        const loadHistory = async () => {
            if (!selectedItem) return;
            try {
                const history = await fetchStockHistory(selectedItem.ticker);
                setHistoryData(history);
            } catch (err) {
                console.error("Failed to fetch history:", err);
            }
        };
        loadHistory();
    }, [selectedItem?.ticker]);

    const [hoverPrice, setHoverPrice] = useState<{ price: number; x: number } | null>(null);
    const [hoveredZone, setHoveredZone] = useState<string | null>(null);

    if (!selectedItem) {
        return (
            <div className="col-span-12 lg:col-span-9 bg-white dark:bg-slate-950 p-6 flex flex-col items-center justify-center h-full text-slate-300 gap-4">
                <div className="p-8 rounded-full bg-slate-50 dark:bg-slate-900 shadow-inner">
                    <Zap className="h-16 w-16 opacity-5 animate-pulse" />
                </div>
                <div className="text-center">
                    <p className="text-lg font-black text-slate-400 dark:text-slate-600 tracking-tight uppercase">Dashboard Ready</p>
                    <p className="text-sm font-medium text-slate-300">请选择一个代码开始深度诊断</p>
                </div>
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

    // RSI Progress Color
    const getRSIColor = (val: number) => {
        if (val > 70) return "bg-rose-500";
        if (val < 30) return "bg-emerald-500";
        return "bg-blue-500";
    };

    return (
        <div className="col-span-12 lg:col-span-9 bg-white dark:bg-slate-950 p-6 md:p-8 flex flex-col gap-8 overflow-y-auto h-full custom-scrollbar w-full max-w-[1400px] mx-auto border-x border-slate-50 dark:border-slate-900 shadow-xl shadow-slate-200/50 dark:shadow-none">

            {/* --- Section 1: Executive Identity --- */}
            <div className="flex flex-col gap-4 border-b border-slate-100 dark:border-slate-800 pb-8">
                <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                        <h1 className="text-4xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                            {selectedItem.name || selectedItem.ticker}
                        </h1>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mt-2">
                            {selectedItem.name ? selectedItem.ticker : "Full Financial Reputation Analysis"}
                        </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-3xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                            ${selectedItem.current_price.toFixed(2)}
                        </span>
                        <div className={clsx(
                            "flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black italic",
                            (selectedItem.change_percent || 0) >= 0 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400"
                        )}>
                            <TrendingUp className={clsx("h-3 w-3", (selectedItem.change_percent || 0) < 0 && "rotate-180")} />
                            {selectedItem.change_percent?.toFixed(2)}%
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
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
                            <span className={clsx("text-md font-bold", selectedItem.unrealized_pl >= 0 ? "text-emerald-500" : "text-rose-500")}>
                                {selectedItem.unrealized_pl >= 0 ? "+" : ""}${selectedItem.unrealized_pl.toFixed(2)}
                            </span>
                            <span className={clsx(
                                "text-[10px] font-black px-1.5 py-0.5 rounded-md",
                                selectedItem.pl_percent >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
                            )}>
                                {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end justify-center">
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-10 px-4 font-black border-2 rounded-xl text-slate-400 hover:text-blue-500 hover:border-blue-500 transition-all duration-1000"
                            onClick={handleRefresh}
                            disabled={refreshing}
                        >
                            <RefreshCw className={clsx("mr-2 h-4 w-4", refreshing && "animate-spin")} />
                            刷新行情
                        </Button>
                    </div>
                </div>
            </div>

            {/* --- Section 1.5: Technical Chart --- */}
            <div className="w-full">
                <StockChart data={historyData} ticker={selectedItem.ticker} />
            </div>

            {/* --- Section 2: AI Verdict (Score & Status) --- */}
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-1.5 bg-blue-600 rounded-full" />
                        <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">AI 智能判研指标</h2>
                    </div>
                    <Button
                        onClick={() => onAnalyze(true)}
                        disabled={analyzing}
                        className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-black px-6 h-10 rounded-xl hover:scale-105 transition-transform active:scale-95"
                    >
                        {analyzing ? "诊断中..." : "开启深度诊断"}
                    </Button>
                </div>

                {aiData ? (
                    <div className="space-y-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none animate-in fade-in slide-in-from-bottom-2 duration-700">

                        {/* 1. Header & Suggested Action (Top) */}
                        <div className="p-6 md:p-8 bg-slate-50/50 dark:bg-white/5 border-b border-slate-100 dark:border-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.3em]">AI Suggested Action</span>
                                    {aiData.rr_ratio && (
                                        <span className="text-[9px] font-black bg-blue-600 text-white px-2 py-0.5 rounded-md italic">R/R {aiData.rr_ratio}</span>
                                    )}
                                </div>
                                <div className="flex items-baseline gap-3">
                                    <h3 className={clsx(
                                        "text-3xl font-black uppercase tracking-tight",
                                        aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多") ? "text-emerald-600 dark:text-emerald-400" :
                                            aiData.immediate_action?.includes("卖") || aiData.immediate_action?.includes("减") ? "text-rose-600 dark:text-rose-400" :
                                                "text-slate-900 dark:text-white"
                                    )}>
                                        {aiData.immediate_action || "观望"}
                                    </h3>
                                    <span className="text-sm font-bold text-blue-600 dark:text-blue-400 italic opacity-80">{aiData.summary_status}</span>
                                </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                                <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-slate-400 uppercase tracking-tighter border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                    <Clock className="h-3 w-3" />
                                    期限: <span className="text-slate-700 dark:text-slate-300 font-black">{aiData.investment_horizon || "未知"}</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-slate-400 uppercase tracking-tighter border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                    <Activity className="h-3 w-3" />
                                    信心: <span className="text-slate-700 dark:text-slate-300 font-black">{aiData.confidence_level || 0}%</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-slate-400 uppercase tracking-tighter border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                    <AlertCircle className="h-3 w-3" />
                                    风险: <span className="text-slate-700 dark:text-slate-300 font-black tracking-widest">{aiData.risk_level || "中"}</span>
                                </div>
                            </div>
                        </div>

                        {/* 2. Trade Range Axis (Middle) */}
                        <div className="p-8 md:p-10 space-y-10">
                            <div className="space-y-6">
                                <div className="flex justify-between items-end">
                                    <div className="space-y-1">
                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">交易执行区间 / Trade Axis</span>
                                        <p className="text-xs font-bold text-slate-500 italic">* 基于当前价 ${selectedItem.current_price.toFixed(2)} 的多维研判</p>
                                    </div>
                                    <div className="flex gap-6">
                                        <div className="flex flex-col items-end">
                                            <span className="text-[9px] font-bold text-slate-400 uppercase">建仓区间</span>
                                            <span className="text-sm font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                                                {aiData.entry_price_low != null && aiData.entry_price_high != null
                                                    ? `$${aiData.entry_price_low.toFixed(2)} - $${aiData.entry_price_high.toFixed(2)}`
                                                    : (aiData.entry_zone || "--")
                                                }
                                            </span>
                                        </div>
                                        <div className="flex flex-col items-end">
                                            <span className="text-[9px] font-bold text-slate-400 uppercase">目标止盈</span>
                                            <span className="text-sm font-black text-blue-600 dark:text-blue-400 tabular-nums">${aiData.target_price?.toFixed(2) || "--"}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* 3. Sentiment Bias Bar (Moved Up per Feedback) */}
                                <div className="space-y-4 pt-4 pb-8 border-b border-slate-100 dark:border-white/5">
                                    <div className="flex justify-between items-center text-[10px] font-extrabold uppercase text-slate-400 tracking-wider">
                                        <div className="flex items-center gap-2">
                                            <Activity className="h-3 w-3 text-indigo-500" />
                                            <span>AI 情绪偏差 / Sentiment Bias</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-slate-900 dark:text-white font-black italic">{aiData.sentiment_score}%</span>
                                            <span className={clsx(
                                                "px-2 py-0.5 rounded text-[8px] font-black uppercase",
                                                (aiData.sentiment_score || 0) > 60 ? "bg-emerald-100 text-emerald-700" :
                                                    (aiData.sentiment_score || 0) < 40 ? "bg-rose-100 text-rose-700" :
                                                        "bg-blue-100 text-blue-700"
                                            )}>
                                                {aiData.sentiment_score && aiData.sentiment_score > 60 ? "Bullish" :
                                                    aiData.sentiment_score && aiData.sentiment_score < 40 ? "Bearish" : "Neutral"}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner p-0.5">
                                        <div
                                            className={clsx(
                                                "h-full rounded-full transition-all duration-1000 ease-out shadow-sm",
                                                (aiData.sentiment_score || 0) > 60 ? "bg-gradient-to-r from-emerald-400 to-emerald-600" :
                                                    (aiData.sentiment_score || 0) < 40 ? "bg-gradient-to-r from-rose-400 to-rose-600" :
                                                        "bg-gradient-to-r from-blue-400 to-blue-600"
                                            )}
                                            style={{ width: `${aiData.sentiment_score || 0}%` }}
                                        />
                                    </div>
                                    <div className="flex justify-between text-[8px] font-black text-slate-400 uppercase tracking-tighter italic opacity-60">
                                        <span>0: 极度看空 (Bear)</span>
                                        <span className="text-center">50: Neutral</span>
                                        <span className="text-right">100: 极度看多 (Bull)</span>
                                    </div>
                                </div>

                                {/* Visual Axis Line - Redesigned as "Action Zones" */}
                                {(() => {
                                    if (!aiData || !aiData.stop_loss_price || !aiData.target_price || !selectedItem) return null;

                                    const stop = aiData.stop_loss_price;
                                    const target = aiData.target_price;
                                    const strategyRange = target - stop;
                                    const buffer = strategyRange * 0.2;

                                    let axisMin = stop - buffer;
                                    let axisMax = target + buffer;

                                    const current = selectedItem.current_price;
                                    if (current < axisMin) axisMin = current - buffer;
                                    if (current > axisMax) axisMax = current + buffer;

                                    const totalRange = axisMax - axisMin;
                                    const getPos = (val: number) => ((val - axisMin) / totalRange) * 100;

                                    const targetPrice = aiData.target_price;
                                    const entryHigh = aiData.entry_price_high || aiData.entry_price_low || aiData.stop_loss_price;
                                    const stopPrice = aiData.stop_loss_price;

                                    const zones = [
                                        { name: "止损", start: axisMin, end: stopPrice, color: "bg-[#F0614D]" },
                                        { name: "买入", start: stopPrice, end: entryHigh, color: "bg-[#3CC68A]" },
                                        { name: "持有", start: entryHigh, end: targetPrice, color: "bg-[#E8EAED] dark:bg-slate-600" },
                                        { name: "止盈", start: targetPrice, end: axisMax, color: "bg-[#3B82F6]" }
                                    ];

                                    // Generate 5 evenly spaced price ticks
                                    const tickCount = 5;
                                    const priceTicks = Array.from({ length: tickCount }, (_, i) => {
                                        const pct = (i / (tickCount - 1)) * 100;
                                        const price = axisMin + ((axisMax - axisMin) * (pct / 100));
                                        return { pct, price };
                                    });

                                    return (
                                        <div className="relative pt-12 pb-8">
                                            {/* Current Price Tooltip - Always visible */}
                                            <div
                                                className="absolute z-20 flex flex-col items-center"
                                                style={{ left: `${getPos(current)}%`, top: '0', transform: 'translateX(-50%)' }}
                                            >
                                                <div className="bg-slate-800 dark:bg-slate-900 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg whitespace-nowrap">
                                                    ${current.toFixed(2)}
                                                </div>
                                                <div className="w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-slate-800 dark:border-t-slate-900" />
                                            </div>

                                            {/* Main Bar Container - Matching sentiment bias bar style */}
                                            <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner p-0.5 mt-2">
                                                <div className="h-full w-full rounded-full flex overflow-hidden">
                                                    {zones.map((zone, idx) => (
                                                        <div
                                                            key={idx}
                                                            className={clsx("h-full", zone.color)}
                                                            style={{ width: `${((zone.end - zone.start) / totalRange) * 100}%` }}
                                                        />
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Current Price Marker - Circle with ring */}
                                            <div
                                                className="absolute z-10"
                                                style={{ left: `${getPos(current)}%`, top: 'calc(3rem + 0.5rem + 0.375rem - 0.5rem)', transform: 'translateX(-50%)' }}
                                            >
                                                <div className="relative">
                                                    {/* Outer glow */}
                                                    <div className="absolute inset-0 w-6 h-6 -m-1 bg-blue-400/30 rounded-full blur-sm" />
                                                    {/* Main circle */}
                                                    <div className="w-4 h-4 bg-white rounded-full border-[3px] border-blue-500 shadow-lg" />
                                                </div>
                                            </div>

                                            {/* Bottom Scale Ruler - Matching sentiment bias style */}
                                            <div className="flex justify-between text-[8px] font-black text-slate-400 uppercase tracking-tighter italic opacity-60 mt-2">
                                                {priceTicks.map((tick, i) => (
                                                    <span key={i} className="tabular-nums">
                                                        {tick.price.toFixed(0)}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )
                                })()}
                            </div>
                        </div>

                        {/* 4. Logical Breakdown (Bottom) */}
                        <div className="p-8 bg-slate-50/40 dark:bg-slate-950/40 border-t border-slate-100 dark:border-white/5">
                            <div className="text-[10px] font-extrabold uppercase text-slate-400 tracking-[0.2em] mb-4 flex items-center gap-2">
                                <Activity className="h-3 w-3" /> 诊断研判逻辑 / LOGICAL BREAKDOWN
                            </div>
                            <div className="prose dark:prose-invert max-w-none text-sm font-semibold leading-relaxed text-slate-600 dark:text-slate-400">
                                <ReactMarkdown>{aiData.action_advice}</ReactMarkdown>
                            </div>
                            {aiData.created_at && (
                                <div className="mt-8 flex items-center justify-end">
                                    <span className="text-[9px] font-bold text-slate-300 uppercase italic">
                                        Report Protocol v2.5 • {formatDistanceToNow(new Date(aiData.created_at + (aiData.created_at.includes('Z') ? '' : 'Z')), { addSuffix: true, locale: zhCN })}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-[2rem] text-slate-400 gap-4">
                        <BarChart3 className="h-10 w-10 opacity-10" />
                        <p className="text-[10px] font-bold uppercase tracking-[0.3em]">等待诊断报告生成...</p>
                    </div>
                )}
            </div>

            {/* --- Section 3: Technical Scan (Visual Hub) --- */}
            <div className="space-y-8">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-emerald-500 rounded-full" />
                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">技术面深度透视 / Technical Scan</h2>
                </div>

                {/* Optimized Layout based on Sketch: 2x2 Visuals + 5-Metric Strip + Full-Width AI */}
                <div className="space-y-12 pt-4">
                    {/* Part 1: Main Visual Matrix (2x2) */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
                        {/* [0,0] RSI & KDJ Matrix */}
                        <div className="space-y-6">
                            <div className="flex justify-between items-center px-1">
                                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-[0.2em] flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-blue-500" /> RSI (14) & KDJ
                                </span>
                                <div className="flex gap-4">
                                    <div className="flex items-center gap-1">
                                        <span className="text-[8px] font-bold text-slate-400">RSI:</span>
                                        <span className="text-xs font-black tabular-nums text-blue-500">{selectedItem.rsi_14?.toFixed(2)}</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="text-[8px] font-bold text-slate-400">KDJ-J:</span>
                                        <span className={clsx(
                                            "text-xs font-black tabular-nums",
                                            (selectedItem.j_line || 0) > 80 ? "text-rose-500" : (selectedItem.j_line || 0) < 20 ? "text-emerald-500" : "text-slate-600"
                                        )}>{selectedItem.j_line?.toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="relative h-1.5 w-full bg-slate-100 dark:bg-slate-800/50 rounded-full overflow-hidden mx-1">
                                <div className="absolute left-[20%] top-0 h-full w-[1px] bg-slate-300 dark:bg-slate-700 z-10" />
                                <div className="absolute left-[80%] top-0 h-full w-[1px] bg-slate-300 dark:bg-slate-700 z-10" />
                                <div
                                    className={clsx("h-full rounded-full transition-all duration-1000", getRSIColor(selectedItem.rsi_14 || 50))}
                                    style={{ width: `${selectedItem.rsi_14 || 0}%` }}
                                />
                            </div>
                            <div className="flex justify-between text-[8px] font-bold text-slate-400 uppercase tracking-widest px-1 opacity-80">
                                <span>Oversold / 超卖</span>
                                <span className="text-slate-300 font-normal">Neutral</span>
                                <span>Overbought / 超买</span>
                            </div>
                        </div>

                        {/* [0,1] MACD Dynamic Matrix */}
                        <div className="space-y-6">
                            <div className="flex justify-between items-center px-1">
                                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-[0.2em] flex items-center gap-2">
                                    <Activity className="h-4 w-4 text-indigo-500" /> MACD 趋势与动能 (日线)
                                </span>
                                <div className="flex gap-2">
                                    <span className={clsx(
                                        "text-[9px] font-black px-2 py-0.5 rounded-full uppercase border tabular-nums",
                                        (selectedItem.macd_hist || 0) >= 0 ? "bg-emerald-50/50 text-emerald-600 border-emerald-100" : "bg-rose-50/50 text-rose-600 border-rose-100"
                                    )}>
                                        {(selectedItem.macd_hist || 0) >= 0 ? "多头" : "空头"}
                                    </span>
                                    {selectedItem.macd_hist_slope !== undefined && (
                                        <span className={clsx(
                                            "text-[9px] font-black px-2 py-0.5 rounded-full uppercase border tabular-nums",
                                            (selectedItem.macd_hist_slope || 0) >= 0 ? "bg-blue-50/50 text-blue-600 border-blue-100" : "bg-amber-50/50 text-amber-600 border-amber-100"
                                        )}>
                                            {(selectedItem.macd_hist_slope || 0) >= 0 ? "动能增强" : "动能减弱"}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="grid grid-cols-4 gap-4 px-1">
                                {[
                                    { label: "快线 DIF", value: selectedItem.macd_val },
                                    { label: "慢线 DEA", value: selectedItem.macd_signal },
                                    { label: "柱状 Hist", value: selectedItem.macd_hist, color: true },
                                    { label: "斜率 Slope", value: selectedItem.macd_hist_slope, color: true },
                                ].map((m) => (
                                    <div key={m.label} className="flex flex-col gap-1">
                                        <span className="text-[8px] font-bold text-slate-400 uppercase tracking-tight">{m.label}</span>
                                        <span className={clsx(
                                            "text-md font-black tabular-nums tracking-tighter",
                                            m.color ? ((m.value || 0) >= 0 ? "text-emerald-500" : "text-rose-500") : "text-slate-800 dark:text-slate-100"
                                        )}>
                                            {m.value?.toFixed(2) || "--"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* [1,0] Bollinger Bands Matrix */}
                        <div className="space-y-6 border-t border-slate-50 dark:border-slate-800 pt-8">
                            <div className="flex justify-between items-center px-1">
                                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-[0.2em] flex items-center gap-2">
                                    <Activity className="h-4 w-4 text-rose-500" /> 布林带 (Bollinger Bands)
                                </span>
                                <span className={clsx(
                                    "text-[9px] font-black px-2 py-0.5 rounded-full uppercase border tabular-nums",
                                    (selectedItem.current_price || 0) > (selectedItem.bb_upper || 0) ? "bg-rose-50 text-rose-600 border-rose-100" :
                                        (selectedItem.current_price || 0) < (selectedItem.bb_lower || 0) ? "bg-emerald-50 text-emerald-600 border-emerald-100" :
                                            "bg-slate-50 text-slate-500 border-slate-100"
                                )}>
                                    {(selectedItem.current_price || 0) > (selectedItem.bb_upper || 0) ? "穿越上轨" :
                                        (selectedItem.current_price || 0) < (selectedItem.bb_lower || 0) ? "跌破下轨" : "带宽内运行"}
                                </span>
                            </div>
                            <div className="grid grid-cols-3 gap-4 px-1">
                                {[
                                    { label: "上轨 UP", value: selectedItem.bb_upper },
                                    { label: "中轨 MID", value: selectedItem.bb_middle },
                                    { label: "下轨 LOW", value: selectedItem.bb_lower },
                                ].map((b) => {
                                    const diffPercent = selectedItem.current_price && b.value
                                        ? ((selectedItem.current_price - b.value) / b.value) * 100
                                        : null;

                                    return (
                                        <div key={b.label} className="flex flex-col gap-1">
                                            <div className="flex justify-between items-baseline">
                                                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-tight">{b.label}</span>
                                                {diffPercent !== null && (
                                                    <span className={clsx(
                                                        "text-[7px] font-bold tabular-nums",
                                                        diffPercent >= 0 ? "text-emerald-500" : "text-rose-500"
                                                    )}>
                                                        {diffPercent >= 0 ? "+" : ""}{diffPercent.toFixed(1)}%
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-md font-black tabular-nums text-slate-800 dark:text-slate-100">
                                                {b.value?.toFixed(2) || "--"}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* [1,1] Moving Averages Matrix */}
                        <div className="space-y-6 border-t border-slate-50 dark:border-slate-800 pt-8">
                            <div className="flex justify-between items-center px-1">
                                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-[0.2em] flex items-center gap-2">
                                    <Target className="h-4 w-4 text-emerald-500" /> 移动平均线 (MA)
                                </span>
                                <div className="flex gap-2">
                                    {((selectedItem.ma_20 || 0) > (selectedItem.ma_50 || 0) && (selectedItem.ma_50 || 0) > (selectedItem.ma_200 || 0)) ? (
                                        <span className="text-[8px] font-black px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100 uppercase">多头排列</span>
                                    ) : (
                                        <span className="text-[8px] font-black px-2 py-0.5 rounded-full bg-slate-50 text-slate-400 border border-slate-100 uppercase">交织运行</span>
                                    )}
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4 px-1">
                                {[
                                    { label: "MA 20 (短)", value: selectedItem.ma_20 },
                                    { label: "MA 50 (中)", value: selectedItem.ma_50 },
                                    { label: "MA 200 (长)", value: selectedItem.ma_200 },
                                ].map((m) => (
                                    <div key={m.label} className="flex flex-col gap-1">
                                        <span className="text-[8px] font-bold text-slate-400 uppercase tracking-tight">{m.label}</span>
                                        <span className="text-md font-black tabular-nums text-slate-800 dark:text-slate-100">
                                            {m.value?.toFixed(2) || "--"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Part 2: Middle Strip (5 Small Metric Cards) */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-6 pt-4">
                        {[
                            { label: "ADX 强度", value: selectedItem.adx_14?.toFixed(2), unit: "", status: (selectedItem.adx_14 || 0) > 25 ? "强趋势" : "震荡" },
                            { label: "ATR 波幅", value: selectedItem.atr_14?.toFixed(2), unit: "$", status: "Volatility" },
                            { label: "量比 (Vol)", value: "X" + (selectedItem.volume_ratio?.toFixed(2) || "--"), unit: "", status: (selectedItem.volume_ratio || 0) > 1.2 ? "放量" : "缩量" },
                            { label: "阻力 R1", value: "$" + (selectedItem.resistance_1?.toFixed(2) || "--"), unit: "", status: "Resistance" },
                            { label: "支撑 S1", value: "$" + (selectedItem.support_1?.toFixed(2) || "--"), unit: "", status: "Support" },
                        ].map((item) => (
                            <div key={item.label} className="bg-slate-50/50 dark:bg-slate-900/30 p-4 rounded-2xl border border-slate-100 dark:border-slate-800/50 flex flex-col items-center justify-center gap-1 shadow-sm">
                                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter whitespace-nowrap">{item.label}</span>
                                <span className="text-md font-black text-slate-900 dark:text-slate-100 tabular-nums">{item.value || "--"}</span>
                                <span className="text-[7px] font-bold text-slate-300 uppercase italic opacity-80">{item.status}</span>
                            </div>
                        ))}
                    </div>

                    {/* Part 3: AI Analysis Insight (Full Width at Bottom) */}
                    <div className="bg-slate-50/30 dark:bg-slate-900/20 p-8 rounded-3xl border-2 border-slate-100 dark:border-slate-800/50 space-y-6">
                        <div className="flex items-center gap-3 text-[10px] font-black uppercase text-blue-600 dark:text-blue-400 tracking-[0.3em] opacity-80">
                            <Zap className="h-4 w-4 fill-current animate-pulse" /> AI Technical Analysis Conclusion
                        </div>
                        {aiData ? (
                            <div className="prose dark:prose-invert max-w-none text-sm font-semibold leading-relaxed text-slate-600 dark:text-slate-400">
                                <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-slate-300 opacity-50">
                                <BarChart3 className="h-8 w-8 mb-3 opacity-20" />
                                <p className="text-[10px] font-black uppercase tracking-[0.2em]">Executing comprehensive technical diagnostics...</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* --- Section 4: Fundamental Identity --- */}
            <div className="space-y-8">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-amber-500 rounded-full" />
                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">基本面资料卡</h2>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-y-10 gap-x-6 border-b border-slate-50 dark:border-slate-800 pb-10">
                    {[
                        { label: "市值", value: selectedItem.market_cap ? (selectedItem.market_cap / 1e9).toFixed(1) + "B" : "-", sub: "Market Cap" },
                        { label: "市盈率", value: selectedItem.pe_ratio?.toFixed(2) || "-", sub: "Trailing PE" },
                        { label: "预测市盈率", value: selectedItem.forward_pe?.toFixed(2) || "-", sub: "Forward PE" },
                        { label: "每股收益", value: selectedItem.eps?.toFixed(2) || "-", sub: "EPS" },
                        { label: "52周最高", value: "$" + (selectedItem.fifty_two_week_high?.toFixed(2) || "-"), sub: "52W High" },
                        { label: "52周最低", value: "$" + (selectedItem.fifty_two_week_low?.toFixed(2) || "-"), sub: "52W Low" },
                        { label: "板块", value: selectedItem.sector || "-", sub: "Sector" },
                        { label: "细分行业", value: selectedItem.industry || "-", sub: "Industry" },
                    ].map(item => (
                        <div key={item.sub} className="flex flex-col gap-1">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">{item.label}</span>
                            <span className="text-md font-black text-slate-800 dark:text-slate-100 truncate">{item.value}</span>
                            <span className="text-[8px] font-bold text-slate-300 uppercase italic leading-none">{item.sub}</span>
                        </div>
                    ))}
                </div>

                {
                    aiData && (
                        <div className="text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400 p-6 bg-slate-50/50 dark:bg-slate-900/20 rounded-2xl border-2 border-slate-100 dark:border-slate-800">
                            <div className="flex items-center gap-2 mb-4 text-[10px] font-black uppercase text-slate-400 italic">
                                <Activity className="h-3 w-3" /> 消息面综述 (Fundamental Summary)
                            </div>
                            <ReactMarkdown>{aiData.fundamental_news}</ReactMarkdown>
                        </div>
                    )
                }
            </div>

            {/* --- Section 5: News Pipeline (The "Bottom" Stream) --- */}
            <div className="space-y-8 pt-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-1.5 bg-slate-900 dark:bg-slate-100 rounded-full" />
                        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">实时资讯流 (News)</h2>
                    </div>
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full">
                        {news.length} Articles
                    </span>
                </div>

                <StockNewsList news={news} />
            </div>

            <div className="mt-20 py-10 border-t border-slate-100 dark:border-slate-800 text-center">
                <p className="text-[10px] font-black text-slate-300 uppercase tracking-[0.5em] italic">End of Analysis Report</p>
            </div>
        </div>
    );
}
