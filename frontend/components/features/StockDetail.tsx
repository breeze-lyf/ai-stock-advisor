"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Zap, RefreshCw, Activity, Newspaper, TrendingUp, BarChart3, Clock, AlertCircle } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { zhCN } from "date-fns/locale";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { PortfolioItem } from "@/types";
import { refreshStock } from "@/lib/api";
import { StockNewsList } from "./StockNewsList";

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
        <div className="col-span-12 lg:col-span-9 bg-white dark:bg-slate-950 p-6 md:p-12 flex flex-col gap-12 overflow-y-auto h-full custom-scrollbar max-w-4xl mx-auto border-x border-slate-50 dark:border-slate-900 shadow-2xl shadow-slate-200/50 dark:shadow-none">

            {/* --- Section 1: Executive Identity --- */}
            <div className="flex flex-col gap-6 border-b border-slate-100 dark:border-slate-800 pb-10">
                <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                        <h1 className="text-8xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                            {selectedItem.ticker}
                        </h1>
                        <p className="text-sm font-bold text-slate-400 uppercase tracking-[0.2em] mt-2">
                            Full Financial Reputation Analysis
                        </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-4xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                            ${selectedItem.current_price.toFixed(2)}
                        </span>
                        <div className={clsx(
                            "flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black italic",
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
                        <span className="text-lg font-bold text-slate-700 dark:text-slate-300">{selectedItem.quantity} Shares</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">持仓均价</span>
                        <span className="text-lg font-bold text-slate-700 dark:text-slate-300">${selectedItem.avg_cost.toFixed(2)}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">账面盈亏</span>
                        <span className={clsx("text-lg font-bold", selectedItem.unrealized_pl >= 0 ? "text-emerald-500" : "text-rose-500")}>
                            {selectedItem.unrealized_pl >= 0 ? "+" : ""}${selectedItem.unrealized_pl.toFixed(2)}
                        </span>
                    </div>
                    <div className="flex flex-col items-end justify-center">
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-10 px-4 font-black border-2 rounded-xl text-slate-400 hover:text-blue-500 hover:border-blue-500 transition-all"
                            onClick={handleRefresh}
                            disabled={refreshing}
                        >
                            <RefreshCw className={clsx("mr-2 h-4 w-4", refreshing && "animate-spin")} />
                            刷新行情
                        </Button>
                    </div>
                </div>
            </div>

            {/* --- Section 2: AI Verdict (Score & Status) --- */}
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-1.5 bg-blue-600 rounded-full" />
                        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">AI 智能判研指标</h2>
                    </div>
                    <Button
                        onClick={() => onAnalyze()}
                        disabled={analyzing}
                        className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-black px-6 rounded-xl hover:scale-105 transition-transform active:scale-95"
                    >
                        {analyzing ? "诊断中..." : "开启深度诊断"}
                    </Button>
                </div>

                {aiData ? (
                    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-700">
                        {/* Sentiment Visual */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-slate-50 dark:bg-slate-900/50 p-8 rounded-3xl border border-slate-100 dark:border-slate-800">
                            <div className="flex flex-col gap-4">
                                <div className="flex items-end gap-2">
                                    <span className="text-7xl font-black text-slate-900 dark:text-white leading-none">{aiData.sentiment_score || "-"}</span>
                                    <span className="text-xs font-bold text-slate-400 uppercase pb-2">Analysis Score</span>
                                </div>
                                <p className="text-xl font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest italic">{aiData.summary_status}</p>
                            </div>

                            <div className="space-y-4">
                                <div className="flex justify-between items-center text-[10px] font-black uppercase text-slate-400">
                                    <span>情绪倾向 (Sentiment Bias)</span>
                                    <span>{aiData.sentiment_score}%</span>
                                </div>
                                <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-600 transition-all duration-1000 ease-out"
                                        style={{ width: `${aiData.sentiment_score || 0}%` }}
                                    />
                                </div>
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 tracking-tighter">
                                    <AlertCircle className="h-3 w-3" />
                                    风险评定: <span className="text-slate-800 dark:text-slate-200 uppercase">{aiData.risk_level}</span>
                                </div>
                            </div>
                        </div>

                        {/* Actionable Advice */}
                        <div className="relative p-10 bg-white dark:bg-slate-900 border-2 border-slate-900 dark:border-slate-100 rounded-[2rem] shadow-[10px_10px_0px_0px_rgba(0,0,0,0.05)] dark:shadow-none transition-transform hover:-translate-y-1">
                            <div className="absolute -top-4 -left-4 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-6 py-2 rounded-2xl text-xs font-black uppercase italic tracking-widest flex items-center gap-2">
                                <Zap className="h-4 w-4 fill-current" /> AI Action Advice
                            </div>
                            <div className="prose dark:prose-invert max-w-none text-xl font-bold leading-relaxed pt-2">
                                <ReactMarkdown>{aiData.action_advice}</ReactMarkdown>
                            </div>
                            {aiData.created_at && (
                                <div className="mt-8 pt-4 border-t border-slate-50 dark:border-slate-800 flex items-center justify-between">
                                    <span className="text-[10px] font-mono text-slate-400 uppercase">Analysis ID: {format(new Date(aiData.created_at + (aiData.created_at.includes('Z') ? '' : 'Z')), 'yyyyMMdd-HHmmss')}</span>
                                    <span className="text-[10px] font-mono text-slate-400 uppercase">Updated: {formatDistanceToNow(new Date(aiData.created_at + (aiData.created_at.includes('Z') ? '' : 'Z')), { addSuffix: true, locale: zhCN })}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="py-20 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-[2rem] text-slate-400 gap-4">
                        <BarChart3 className="h-12 w-12 opacity-10" />
                        <p className="text-xs font-bold uppercase tracking-[0.3em]">等待诊断报告生成...</p>
                    </div>
                )}
            </div>

            {/* --- Section 3: Technical Scan (Horizontal Flow) --- */}
            <div className="space-y-8">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-emerald-500 rounded-full" />
                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">技术面深度透视</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div className="space-y-6">
                        <div className="flex justify-between items-center text-[10px] font-black uppercase text-slate-500 tracking-widest">
                            <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3" /> RSI (14) 指数</span>
                            <span className={clsx(
                                "font-mono text-sm px-2 py-0.5 rounded",
                                (selectedItem.rsi_14 || 0) > 70 ? "bg-rose-50 text-rose-600" : (selectedItem.rsi_14 || 0) < 30 ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600"
                            )}>{selectedItem.rsi_14?.toFixed(2)}</span>
                        </div>
                        <div className="relative h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full">
                            <div className="absolute left-[30%] top-0 h-full w-0.5 bg-slate-300 dark:bg-slate-600 z-10" />
                            <div className="absolute left-[70%] top-0 h-full w-0.5 bg-slate-300 dark:bg-slate-600 z-10" />
                            <div
                                className={clsx("h-full rounded-full transition-all duration-1000", getRSIColor(selectedItem.rsi_14 || 50))}
                                style={{ width: `${selectedItem.rsi_14 || 0}%` }}
                            />
                            <div className="flex justify-between mt-2 text-[8px] font-black text-slate-400 px-1 uppercase tracking-tighter font-serif italic">
                                <span>Oversold</span>
                                <span>Neutral</span>
                                <span>Overbought</span>
                            </div>
                        </div>

                        {aiData && (
                            <div className="text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/40 p-5 rounded-2xl border-l-4 border-emerald-500 italic">
                                <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {[
                            { label: "MA 20", value: selectedItem.ma_20?.toFixed(2), unit: "$" },
                            { label: "MA 50", value: selectedItem.ma_50?.toFixed(2), unit: "$" },
                            { label: "MACD", value: selectedItem.macd_val?.toFixed(2), unit: "" },
                            { label: "MACD Hist", value: selectedItem.macd_hist?.toFixed(2), unit: "" },
                            { label: "ATR (14)", value: selectedItem.atr_14?.toFixed(2), unit: "" },
                            { label: "Vol Ratio", value: selectedItem.volume_ratio?.toFixed(2), unit: "x" },
                        ].map(item => (
                            <div key={item.label} className="flex flex-col border-b border-slate-50 dark:border-slate-800 py-3">
                                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{item.label}</span>
                                <span className="text-lg font-black text-slate-700 dark:text-slate-300 tabular-nums">
                                    {item.unit}{item.value || "-"}
                                </span>
                            </div>
                        ))}
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

                {aiData && (
                    <div className="text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400 p-6 bg-slate-50/50 dark:bg-slate-900/20 rounded-2xl border-2 border-slate-100 dark:border-slate-800">
                        <div className="flex items-center gap-2 mb-4 text-[10px] font-black uppercase text-slate-400 italic">
                            <Activity className="h-3 w-3" /> 消息面综述 (Fundamental Summary)
                        </div>
                        <ReactMarkdown>{aiData.fundamental_news}</ReactMarkdown>
                    </div>
                )}
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
