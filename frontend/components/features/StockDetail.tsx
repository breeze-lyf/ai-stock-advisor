/**
 * 股票详情面板 (Stock Detail Panel)
 * 职责：作为详情页的高级容器，负责协调行情刷新、K 线图渲染、AI 深度研判展示及新闻列表
 * 核心逻辑：管理图表层级切换、处理 AI 分析结果的视觉映射（如交易轴 Trade Axis）
 */
"use client";

import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Zap, RefreshCw, Activity, Newspaper, TrendingUp, BarChart3, Clock, AlertCircle, Target, ShieldAlert, ShieldCheck, Settings2, ChevronLeft } from "lucide-react";
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
    onBack?: () => void;
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
    refreshTimestamp?: number;
}
export function StockDetail({
    selectedItem,
    onAnalyze,
    onRefresh,
    onBack,
    analyzing,
    aiData,
    news = [],
    refreshTimestamp
}: StockDetailProps) {
    // --- 辅助工具 (Helper Utilities) ---
    const sanitizePrice = (val: number | null | undefined): string => {
        if (val === null || val === undefined || isNaN(val)) return "--";
        return val.toFixed(2);
    };

    const getCurrencySymbol = (ticker: string) => {
        const isCN = /^\d{6}/.test(ticker) || ticker.toUpperCase().endsWith('.SS') || ticker.toUpperCase().endsWith('.SZ');
        return isCN ? "¥" : "$";
    };

    const currency = selectedItem ? getCurrencySymbol(selectedItem.ticker) : "$";

    // --- 状态管理 (State Management) ---
    const [refreshing, setRefreshing] = useState(false);
    const [historyData, setHistoryData] = useState<any[]>([]); // 存储 K 线历史数据
    const [historyLoading, setHistoryLoading] = useState(false);
    const [showBb, setShowBb] = useState(true);   // 布林带显示开关
    const [showRsi, setShowRsi] = useState(false); // RSI 显示开关
    const [showMacd, setShowMacd] = useState(false); // MACD 显示开关
    const [isScrolled, setIsScrolled] = useState(false); // 滚动状态，用于触发粘性顶栏
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const handleScroll = () => {
            const scrollThreshold = 80;
            if (container.scrollTop > scrollThreshold) {
                setIsScrolled(true);
            } else {
                setIsScrolled(false);
            }
        };

        container.addEventListener("scroll", handleScroll);
        // Reset scroll when item changes
        container.scrollTop = 0;
        setIsScrolled(false);
        
        return () => container.removeEventListener("scroll", handleScroll);
    }, [selectedItem?.ticker]);

    useEffect(() => {
        const loadHistory = async () => {
            if (!selectedItem) return;
            setHistoryLoading(true);
            try {
                const history = await fetchStockHistory(selectedItem.ticker);
                setHistoryData(history);
            } catch (err) {
                console.error("Failed to fetch history:", err);
            } finally {
                setHistoryLoading(false);
            }
        };
        loadHistory();
    }, [selectedItem?.ticker, refreshTimestamp]);

    const [hoverPrice, setHoverPrice] = useState<{ price: number; x: number } | null>(null);
    const [hoveredZone, setHoveredZone] = useState<string | null>(null);

    if (!selectedItem) {
        return (
            <div className="flex-1 bg-white dark:bg-zinc-950 p-6 flex flex-col items-center justify-center h-full text-slate-300 gap-4">
                <div className="p-8 rounded-full bg-slate-50 dark:bg-zinc-900 shadow-inner">
                    <Zap className="h-16 w-16 opacity-5 animate-pulse" />
                </div>
                <div className="text-center">
                    <p className="text-lg font-black text-slate-400 dark:text-slate-600 tracking-tight uppercase">终端就绪</p>
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
        <div 
            ref={containerRef}
            className="flex-1 bg-white dark:bg-zinc-950 px-4 md:px-8 pb-12 flex flex-col gap-6 md:gap-8 overflow-y-auto h-full custom-scrollbar w-full max-w-[1400px] mx-auto relative"
        >
            {/* --- Sticky Bar (Visible only when scrolled) --- */}
            <div className={clsx(
                "sticky top-0 z-50 -mx-6 md:-mx-8 px-6 md:px-8 py-2 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-xl border-b border-slate-100 dark:border-zinc-800 transition-all duration-300",
                isScrolled ? "opacity-100 translate-y-0 pointer-events-auto shadow-sm" : "opacity-0 translate-y-[-100%] pointer-events-none"
            )} style={{ marginBottom: "-5.5rem" }}>
                <div className="flex md:items-center justify-between gap-4 h-14">
                    <div className="flex items-center gap-2 md:gap-4">
                        {onBack && (
                            <button onClick={onBack} title="返回" aria-label="返回" className="lg:hidden p-1 -ml-1 rounded-full text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
                                <ChevronLeft className="h-6 w-6" />
                            </button>
                        )}
                        <div className="flex flex-col">
                            <h1 className="text-lg font-black tracking-tighter text-slate-900 dark:text-white leading-tight">
                                {selectedItem.name || selectedItem.ticker}
                            </h1>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">
                                {selectedItem.ticker}
                            </span>
                        </div>
                        
                        <div className="h-6 w-px bg-slate-100 dark:bg-slate-800 mx-1 hidden md:block" />

                        <div className="flex items-center gap-3">
                            <span className="text-lg font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                                {currency}{sanitizePrice(selectedItem.current_price)}
                            </span>
                            {selectedItem.quantity > 0 && (
                                <div className={clsx(
                                    "flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-black italic",
                                    (selectedItem.pl_percent || 0) >= 0 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400"
                                )}>
                                    <TrendingUp className={clsx("h-3 w-3", (selectedItem.pl_percent || 0) < 0 && "rotate-180")} />
                                    {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                                </div>
                            )}
                            {selectedItem.market_status === "PRE_MARKET" && (
                                <span className="text-[10px] px-2 py-0.5 rounded-md bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 font-black border border-orange-200 dark:border-orange-500/20 leading-none">
                                    PRE
                                </span>
                            )}
                            {selectedItem.market_status === "AFTER_HOURS" && (
                                <span className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-500/10 text-slate-500 dark:text-slate-400 font-black border border-slate-200 dark:border-slate-500/20 leading-none">
                                    POST
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="hidden sm:flex flex-col items-end">
                            <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">最新增幅</span>
                            <span className={clsx("text-sm font-black tabular-nums", (selectedItem.change_percent || 0) >= 0 ? "text-emerald-500" : "text-rose-500")}>
                                {(selectedItem.change_percent || 0) >= 0 ? "+" : ""}{(selectedItem.change_percent || 0).toFixed(2)}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* --- Section 1: Executive Identity (Full Header, fades out when scrolled) --- */}
            <div className={clsx(
                "flex flex-col gap-2 border-b border-slate-100 dark:border-slate-800 pb-3 pt-4 transition-all duration-500",
                isScrolled && "opacity-0 pointer-events-none"
            )}>
                <div className="flex flex-col sm:flex-row justify-between sm:items-end gap-3 sm:gap-4">
                    <div className="flex items-start gap-2">
                        {onBack && (
                            <button onClick={onBack} title="返回" aria-label="返回" className="lg:hidden mt-1 p-1 -ml-1 rounded-full text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors">
                                <ChevronLeft className="h-7 w-7" />
                            </button>
                        )}
                        <div className="flex flex-col">
                            <div className="flex items-center gap-3">
                                <h1 className="text-3xl md:text-4xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
                                    {selectedItem.name || selectedItem.ticker}
                                </h1>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 rounded-full text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-300"
                                    onClick={handleRefresh}
                                    disabled={refreshing}
                                    title="刷新行情"
                                >
                                    <RefreshCw className={clsx("h-4 w-4", refreshing && "animate-spin")} />
                                </Button>
                            </div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mt-2">
                                {selectedItem.name ? selectedItem.ticker : "全维度财务声誉分析"}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-6 sm:gap-10">
                        {/* --- Latest Growth (Daily Change) --- */}
                        <div className="hidden sm:flex flex-col items-end">
                            <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">最新涨跌</span>
                            <span className={clsx("text-lg font-black tabular-nums", (selectedItem.change_percent || 0) >= 0 ? "text-emerald-500" : "text-rose-500")}>
                                {(selectedItem.change_percent || 0) >= 0 ? "+" : ""}{selectedItem.change_percent?.toFixed(2)}%
                            </span>
                        </div>

                        {/* --- Price & Portfolio P/L Badge --- */}
                        <div className="flex flex-col items-end gap-1">
                            <span className="text-3xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
                                ${selectedItem.current_price.toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>

                {selectedItem.quantity > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-50 dark:border-slate-800/50">
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
                                    selectedItem.pl_percent >= 0 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400" : "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400"
                                )}>
                                    {selectedItem.pl_percent >= 0 ? "+" : ""}{selectedItem.pl_percent.toFixed(2)}%
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* --- Section 1.5: Technical Chart --- */}
            <div className="space-y-8">
                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between px-2">
                        <div className="flex items-center gap-3">
                            <div className="h-8 w-1.5 bg-blue-500 rounded-full" />
                            <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">动态行情分析</h2>
                        </div>
                        
                        <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800/50 p-1 rounded-xl">
                            <div className="px-3 py-1.5 text-[9px] font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                                <Settings2 className="h-3 w-3" /> 图层控制
                            </div>
                            <button
                                onClick={() => setShowBb(!showBb)}
                                className={clsx(
                                    "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                    showBb ? "bg-slate-700 text-white shadow-md" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                )}
                            >
                                BB
                            </button>
                            <button
                                onClick={() => setShowRsi(!showRsi)}
                                className={clsx(
                                    "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                    showRsi ? "bg-blue-500 text-white shadow-md shadow-blue-500/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                )}
                            >
                                RSI
                            </button>
                            <button
                                onClick={() => setShowMacd(!showMacd)}
                                className={clsx(
                                    "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                    showMacd ? "bg-indigo-500 text-white shadow-md shadow-indigo-500/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                )}
                            >
                                MACD
                            </button>
                        </div>
                    </div>
                    
                    <div className="relative group">
                        <StockChart 
                            data={historyData} 
                            ticker={selectedItem.ticker} 
                            showBb={showBb}
                            showRsi={showRsi} 
                            showMacd={showMacd} 
                        />
                    </div>
                </div>
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
                    (() => {
                    /**
                     * 交易轴算法逻辑 (Trade Axis Algorithm)
                     * 职责：将 AI 提供的 止损/建仓/目标价 映射到一个线性坐标轴上
                     * 逻辑：
                     * 1. 计算策略核心极差 (Strategy Range)
                     * 2. 增加 20% 的视觉缓冲 (Buffer) 以确保指针不会由于紧贴边缘而无法阅读
                     * 3. 计算当前价在坐标轴上的百分比位置 (getPos)
                     */
                    const stop = aiData.stop_loss_price || 0;
                    const target = aiData.target_price || 0;
                    const current = selectedItem.current_price;
                    const entryLow = aiData.entry_price_low || stop;
                    const entryHigh = aiData.entry_price_high || entryLow;
                    
                    const strategyRange = target - stop;
                    const buffer = strategyRange * 0.2;

                    let axisMin = stop - buffer;
                    let axisMax = target + buffer;

                    if (current < axisMin) axisMin = current - buffer;
                    if (current > axisMax) axisMax = current + buffer;

                    const totalRange = axisMax - axisMin;
                    const getPos = (val: number) => ((val - axisMin) / totalRange) * 100;

                    const zones = [
                        { name: (selectedItem?.quantity || 0) > 0 ? "止损" : "预设止损", start: axisMin, end: stop, color: "bg-[#F0614D]", textColor: "text-rose-600" },
                        { name: "建仓", start: stop, end: entryHigh, color: "bg-[#3CC68A]", textColor: "text-emerald-600" },
                        { name: "观望/持有", start: entryHigh, end: target, color: "bg-[#E8EAED] dark:bg-slate-600", textColor: "text-slate-500" },
                        { name: "止盈", start: target, end: axisMax, color: "bg-[#3B82F6]", textColor: "text-blue-600" }
                    ];

                    const activeZone = zones.find(z => current >= z.start && current <= z.end) || 
                                     (current < axisMin ? zones[0] : zones[zones.length-1]);

                    // Use backend-provided R/R ratio strictly
                    const effectiveRR = aiData.rr_ratio;

                    return (
                        <div className="space-y-0 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-3xl overflow-hidden shadow-xl shadow-slate-200/50 dark:shadow-none animate-in fade-in slide-in-from-bottom-2 duration-700">

                        {/* 1. Header & Sentiment Grid */}
                        <div className="p-6 md:p-8 bg-slate-50/50 dark:bg-white/5 border-b border-slate-100 dark:border-white/5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
                                {/* Left Side: Suggested Action */}
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <h3 className={clsx(
                                            "text-3xl font-black uppercase tracking-tight",
                                            aiData.immediate_action?.includes("买") || aiData.immediate_action?.includes("多") ? "text-slate-900 dark:text-white" :
                                                aiData.immediate_action?.includes("卖") || aiData.immediate_action?.includes("减") ? "text-rose-600 dark:text-rose-400" :
                                                    "text-slate-900 dark:text-white"
                                        )}>
                                            {aiData.immediate_action || "观望"}
                                        </h3>
                                        <span className={clsx(
                                            "text-[9px] font-black px-2 py-0.5 rounded-md border uppercase",
                                            activeZone.textColor.replace("text-", "bg-").replace("600", "50") + "/50",
                                            activeZone.textColor,
                                            activeZone.textColor.replace("text-", "border-").replace("600", "200")
                                        )}>
                                            {activeZone.name}
                                        </span>
                                            <div className={clsx(
                                            "flex items-center gap-1.5 px-2 py-0.5 rounded-md border ml-1",
                                            parseFloat(effectiveRR || "0") >= 2.5 ? "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20" :
                                            parseFloat(effectiveRR || "0") >= 1.8 ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20" :
                                            "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20"
                                        )}>
                                            <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70">盈亏比 R/R</span>
                                            <span className="text-[10px] font-black tabular-nums">{effectiveRR || "--"}</span>
                                        </div>
                                        {selectedItem.market_status === "PRE_MARKET" && (
                                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-orange-200 bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400 dark:border-orange-500/20 ml-1">
                                                <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘前 PRE</span>
                                            </div>
                                        )}
                                        {selectedItem.market_status === "AFTER_HOURS" && (
                                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md border border-slate-200 bg-slate-50 text-slate-500 dark:bg-slate-500/10 dark:text-slate-400 dark:border-slate-500/20 ml-1">
                                                <span className="text-[8px] font-bold uppercase tracking-tighter opacity-70 italic">盘后 POST</span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-sm font-semibold text-blue-600 dark:text-blue-500 opacity-90">{aiData.summary_status || "技术修复中"}</span>
                                    </div>
                                    
                                    <div className="flex flex-wrap items-center gap-2 pt-1">
                                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                            <Clock className="h-3 w-3 text-blue-400" />
                                            期限：<span className="text-slate-900 dark:text-slate-200">{aiData.investment_horizon || "中期"}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                            <Zap className="h-3 w-3 text-blue-400" />
                                            信心：<span className="text-slate-900 dark:text-slate-200">{aiData.confidence_level || "72"}%</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-500 uppercase tracking-tighter border-2 border-slate-100 dark:border-slate-800 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-950 shadow-sm">
                                            <AlertCircle className="h-3 w-3 text-blue-400" />
                                            风险：<span className="text-slate-900 dark:text-slate-200">{aiData.risk_level || "中"}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Right Side: Sentiment Bias */}
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center text-[11px] font-black uppercase text-slate-400 tracking-[0.3em]">
                                        <div className="flex items-center gap-3">
                                            <Activity className="h-4 w-4 text-blue-500" />
                                            <span>AI 情绪偏差</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-slate-900 dark:text-white font-black italic">{aiData.sentiment_score || 58}%</span>
                                            <span className={clsx(
                                                "px-2 py-0.5 rounded-md border text-[9px] font-black uppercase",
                                                (aiData.sentiment_score || 0) > 60 ? "bg-emerald-50 text-emerald-600 border-emerald-200" :
                                                    (aiData.sentiment_score || 0) < 40 ? "bg-rose-50 text-rose-600 border-rose-200" :
                                                        "bg-blue-50 text-blue-600 border-blue-200"
                                            )}>
                                                {aiData.sentiment_score && aiData.sentiment_score > 60 ? "Bullish" :
                                                    aiData.sentiment_score && aiData.sentiment_score < 40 ? "Bearish" : "Neutral"}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0">
                                        <div
                                            className="h-full rounded-full transition-all duration-1000 ease-out bg-blue-500"
                                            style={{ width: `${aiData.sentiment_score || 58}%` }}
                                        />
                                    </div>
                                    <div className="flex justify-between text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                                        <span>0: 极度看空</span>
                                        <span className="text-center">50: 中性</span>
                                        <span className="text-right">100: 极度看多</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 2. Trade Range Axis (Middle) */}
                        <div className="p-6 space-y-4">
                            <div className="space-y-4">
                                <div className="flex justify-between items-end">
                                    <div className="space-y-1">
                                        <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                            <Target className="h-3.5 w-3.5 text-blue-500" />
                                            <span>交易执行区间</span>
                                        </div>
                                        <p className="text-[10px] font-medium text-slate-400 italic opacity-80 ml-5.5">* 基于当前价的深度研判</p>
                                    </div>
                                    <div className="flex gap-6">
                                        <div className="flex flex-col items-end gap-0.5">
                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">
                                                {(selectedItem?.quantity || 0) > 0 ? "止损" : "预设止损"}
                                            </span>
                                            <span className={clsx(
                                                "text-md font-black tabular-nums",
                                                (selectedItem?.quantity || 0) > 0 ? "text-rose-500 dark:text-rose-400" : "text-rose-400 dark:text-rose-500/80"
                                            )}>
                                                ${aiData.stop_loss_price?.toFixed(2) || "--"}
                                            </span>
                                        </div>
                                        <div className="flex flex-col items-end gap-0.5">
                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">建仓区间</span>
                                            <span className="text-md font-black text-emerald-500 dark:text-emerald-400 tabular-nums">
                                                {aiData.entry_price_low != null && aiData.entry_price_high != null
                                                    ? `$${aiData.entry_price_low.toFixed(2)} - $${aiData.entry_price_high.toFixed(2)}`
                                                    : (aiData.entry_zone || "--")
                                                }
                                            </span>
                                        </div>
                                        <div className="flex flex-col items-end gap-0.5">
                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">目标止盈</span>
                                            <span className="text-md font-black text-blue-500 dark:text-blue-400 tabular-nums">${aiData.target_price?.toFixed(2) || "--"}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Visual Axis Line */}
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

                                    const stopPrice = aiData.stop_loss_price;
                                    const entryLow = aiData.entry_price_low || stopPrice;
                                    const entryHigh = aiData.entry_price_high || entryLow;
                                    const targetPrice = aiData.target_price;

                                    const isHolding = (selectedItem?.quantity || 0) > 0;
                                    
                                    // 核心：过滤掉重复或无效的区间
                                    const rawZones = [
                                        { name: isHolding ? "止损" : "预设止损", start: axisMin, end: stopPrice, color: isHolding ? "bg-[#F0614D]" : "bg-[repeating-linear-gradient(45deg,transparent,transparent_4px,rgba(240,97,77,0.5)_4px,rgba(240,97,77,0.5)_8px)] opacity-90 border-y border-[#F0614D]/40" },
                                        { name: "观察", start: stopPrice, end: entryLow, color: "bg-[#E8EAED] dark:bg-slate-600 opacity-30" },
                                        { name: "买入", start: entryLow, end: entryHigh, color: "bg-[#3CC68A]" },
                                        { name: "持有", start: entryHigh, end: targetPrice, color: "bg-[#E8EAED] dark:bg-slate-600" },
                                        { name: "止盈", start: targetPrice, end: axisMax, color: "bg-[#3B82F6]" }
                                    ];

                                    const visibleZones = rawZones.filter(z => z.end > z.start);

                                    // 生成关键价位刻度 (Key Price Ticks)
                                    // 逻辑：不再等分，而是直接显示 止损、建仓下限、建仓上限、目标价
                                    const keyPrices = [
                                        { val: stopPrice, label: "止损" },
                                        { val: entryLow, label: "建仓" },
                                        { val: entryHigh, label: "加码" },
                                        { val: targetPrice, label: "目标" }
                                    ].filter((item, index, self) => 
                                        // 过滤掉极其接近的重复价位
                                        index === self.findIndex((t) => Math.abs(t.val - item.val) < 0.01)
                                    ).sort((a, b) => a.val - b.val);

                                     return (
                                        <div className="relative pt-12 pb-2">
                                            <div className="relative">
                                                {/* Main Bar Container */}
                                                <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0">
                                                    <div className="h-full w-full flex overflow-hidden">
                                                        {visibleZones.map((zone, idx) => (
                                                            <div
                                                                key={idx}
                                                                className={clsx("h-full", zone.color)}
                                                                style={{ width: `${((zone.end - zone.start) / totalRange) * 100}%` }}
                                                            />
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* Tooltip & Marker Dot Group */}
                                                <div 
                                                    className="absolute top-1/2 -translate-y-1/2 z-20 flex flex-col items-center"
                                                    style={{ left: `${getPos(current)}%`, transition: 'left 0.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
                                                >
                                                    {/* Tooltip */}
                                                    <div className="absolute bottom-full mb-2 flex flex-col items-center">
                                                        <div className="bg-slate-900 dark:bg-black text-white text-[10px] font-black px-2.5 py-1 rounded-lg shadow-2xl border border-white/10 whitespace-nowrap">
                                                            ${sanitizePrice(current)}
                                                        </div>
                                                        <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-t-[4px] border-l-transparent border-r-transparent border-t-slate-900 dark:border-t-black -mt-px" />
                                                    </div>

                                                    {/* Marker Dot */}
                                                    <div className="w-4 h-4 bg-blue-500 rounded-full border-[3px] border-white dark:border-slate-950 shadow-lg ring-4 ring-blue-500/10" />
                                                </div>
                                            </div>

                                            {/* Key Price Labels (Positioned exactly below the bar) */}
                                            <div className="relative h-6 mt-4">
                                                {keyPrices.map((tick, i) => (
                                                    <div 
                                                        key={i} 
                                                        className="absolute flex flex-col items-center -translate-x-1/2"
                                                        style={{ left: `${getPos(tick.val)}%` }}
                                                    >
                                                        <div className="w-px h-1.5 bg-slate-200 dark:bg-slate-700 mb-1" />
                                                        <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 tabular-nums">
                                                            {tick.val.toFixed(2)}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )
                                })()}
                            </div>
                        </div>

                        {/* 4. Logical Breakdown (Bottom) */}
                        <div className="pt-5 px-6 pb-2.5 bg-slate-50/10 dark:bg-white/5 border-t border-slate-100 dark:border-white/5 space-y-1">
                            <div className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                <Activity className="h-3.5 w-3.5 text-blue-500" />
                                <span>诊断研判逻辑</span>
                            </div>
                            <div className="prose dark:prose-invert max-w-none text-[13px] font-normal leading-relaxed text-slate-500 dark:text-slate-400 [&>p]:m-0">
                                <ReactMarkdown
                                    components={{
                                        h3: ({ node, ...props }) => (
                                            <h3 className="text-sm font-bold text-slate-800 dark:text-white mt-4 mb-2 flex items-center gap-2 border-l-4 border-blue-500 pl-3 tracking-wider" {...props} />
                                        ),
                                        strong: ({ node, ...props }) => (
                                            <strong className="font-bold text-slate-900 dark:text-white px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-500/10" {...props} />
                                        ),
                                        ul: ({ node, ...props }) => (
                                            <ul className="space-y-1 mt-2 list-none p-0" {...props} />
                                        ),
                                        li: ({ node, ...props }) => (
                                            <li className="flex items-start gap-2 before:content-['•'] before:text-blue-500 before:font-black" {...props} />
                                        ),
                                        p: ({ node, ...props }) => (
                                            <p className="mt-1.5 text-slate-500 dark:text-slate-400" {...props} />
                                        )
                                    }}
                                >
                                    {aiData.action_advice}
                                </ReactMarkdown>
                            </div>
                            {aiData.created_at && (
                                <div className="flex items-center justify-end">
                                    <span className="text-[8px] font-bold text-slate-400 dark:text-slate-500 uppercase italic tracking-widest opacity-60">
                                        REPORT PROTOCOL V2.5 • {formatDistanceToNow(new Date(aiData.created_at + (aiData.created_at.includes('Z') ? '' : 'Z')), { addSuffix: true, locale: zhCN })}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                )})()) : (
                    <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-[2rem] text-slate-400 gap-4">
                        <BarChart3 className="h-10 w-10 opacity-10" />
                        <p className="text-[10px] font-bold uppercase tracking-[0.3em]">等待诊断报告生成...</p>
                    </div>
                )}
            </div>

            {/* --- Section 3: Technical Scan (Visual Hub) --- */}
            <div className="space-y-8 relative">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-1.5 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.5)]" />
                        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-zinc-100 uppercase">技术面深度透视</h2>
                    </div>
                </div>

                {/* Dashboard Background & Grid Overlay */}
                <div className="absolute inset-0 -z-10 bg-slate-50/50 dark:bg-zinc-900/20 rounded-[40px] pointer-events-none overflow-hidden border border-slate-100 dark:border-zinc-800/50">
                    <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]" 
                         style={{ backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
                    <div className="absolute top-0 left-1/4 w-1/2 h-1/2 bg-blue-500/5 dark:bg-blue-400/5 blur-[120px] rounded-full" />
                    <div className="absolute bottom-0 right-1/4 w-1/2 h-1/2 bg-emerald-500/5 dark:bg-emerald-400/5 blur-[120px] rounded-full" />
                </div>

                <div className="px-4 md:px-8 py-8 space-y-10">
                    {/* Part 1: AI Technical Conclusion (Full Width Top) */}
                    <div className="relative group">
                        <div className="absolute -inset-px bg-gradient-to-r from-blue-500/20 to-emerald-500/20 rounded-3xl blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                        <div className="relative bg-white/80 dark:bg-zinc-900/50 backdrop-blur-xl border border-slate-200/60 dark:border-zinc-800/80 p-6 md:p-8 rounded-3xl shadow-sm space-y-4">
                            <div className="flex items-center gap-3 text-[10px] font-black uppercase text-blue-600 dark:text-blue-400 tracking-[0.3em] opacity-80">
                                <Zap className="h-4 w-4 fill-current animate-pulse" /> AI Technical Intelligence
                            </div>
                            {aiData ? (
                                <div className="prose dark:prose-invert max-w-none">
                                    <div className="text-base font-bold text-slate-700 dark:text-zinc-300 leading-relaxed italic border-l-4 border-blue-500/30 pl-4 py-1">
                                        <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-6 text-slate-300 opacity-50">
                                    <BarChart3 className="h-8 w-8 mb-3 opacity-20 animate-bounce" />
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em]">Synthesizing technical signals...</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Part 2: Dynamic Indicator Matrix (2 Columns) */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* RSI & KDJ Card */}
                        <div className="bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md border border-slate-100 dark:border-zinc-800/50 p-6 rounded-3xl space-y-6 hover:border-blue-500/30 transition-colors group">
                            <div className="flex justify-between items-center">
                                <span className="text-[10px] font-bold uppercase text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-blue-500" /> RSI (14) & KDJ
                                </span>
                                <div className="flex gap-4 items-baseline">
                                    <span className="text-2xl font-black tabular-nums text-blue-500">{selectedItem?.rsi_14?.toFixed(2)}</span>
                                    <div className="flex items-center gap-1.5 border-l border-slate-100 dark:border-zinc-800/80 pl-3">
                                        <span className="text-xs font-bold text-blue-400">{selectedItem?.k_line?.toFixed(0)}</span>
                                        <span className="text-xs font-bold text-amber-400">{selectedItem?.d_line?.toFixed(0)}</span>
                                        <span className={clsx("text-xs font-black", (selectedItem?.j_line || 0) > 80 ? "text-rose-400" : "text-emerald-400")}>
                                            {selectedItem?.j_line?.toFixed(0)}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="relative h-2 w-full bg-slate-100 dark:bg-zinc-800/80 rounded-full overflow-hidden">
                                <div className="absolute left-[20%] top-0 h-full w-px bg-slate-300 dark:bg-zinc-700 z-10" />
                                <div className="absolute left-[80%] top-0 h-full w-px bg-slate-300 dark:bg-zinc-700 z-10" />
                                <div
                                    className={clsx("h-full rounded-full transition-all duration-1000", getRSIColor(selectedItem?.rsi_14 || 50))}
                                    style={{ width: `${selectedItem?.rsi_14 || 0}%` }}
                                />
                            </div>
                            <div className="flex justify-between text-[8px] font-bold text-slate-400 uppercase tracking-widest px-1">
                                <span>Oversold</span>
                                <span className="text-slate-300 dark:text-zinc-600">Neutral Zone</span>
                                <span>Overbought</span>
                            </div>
                        </div>

                        {/* MACD Card */}
                        <div className="bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md border border-slate-100 dark:border-zinc-800/50 p-6 rounded-3xl space-y-6 hover:border-indigo-500/30 transition-colors">
                            <div className="flex justify-between items-start">
                                <span className="text-[10px] font-bold uppercase text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                    <Activity className="h-4 w-4 text-indigo-500" /> MACD Momentum
                                </span>
                                <div className="flex flex-col items-end gap-1">
                                    <span className={clsx(
                                        "text-[10px] font-black px-3 py-1 rounded-full uppercase shadow-sm",
                                        selectedItem?.macd_cross === "GOLDEN" ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
                                    )}>
                                        {selectedItem?.macd_cross === "GOLDEN" ? "Golden Cross" : "Death Cross"}
                                    </span>
                                    <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest italic">Signal Persistence</span>
                                </div>
                            </div>
                            
                            <div className="grid grid-cols-4 gap-2">
                                {[
                                    { label: "DIF", val: selectedItem?.macd_val },
                                    { label: "DEA", val: selectedItem?.macd_signal },
                                    { label: "HIST", val: selectedItem?.macd_hist, special: true },
                                    { label: "SLOPE", val: selectedItem?.macd_hist_slope, special: true }
                                ].map((m) => (
                                    <div key={m.label} className="bg-slate-50/50 dark:bg-zinc-800/30 p-2.5 rounded-2xl border border-slate-100/50 dark:border-zinc-800/50">
                                        <div className="text-[8px] font-bold text-slate-400 uppercase mb-1">{m.label}</div>
                                        <div className={clsx(
                                            "text-xs font-black tabular-nums",
                                            m.special ? ((m.val || 0) >= 0 ? "text-emerald-500" : "text-rose-500") : "text-slate-700 dark:text-zinc-200"
                                        )}>
                                            {m.val?.toFixed(2) || "0.00"}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Part 3: Support/Execution Strip (3 Columns) */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Bollinger Bands */}
                        <div className="bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md border border-slate-100 dark:border-zinc-800/50 p-5 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 transition-all">
                            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Zap className="h-3.5 w-3.5 text-rose-400" /> Bollinger Bands
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between items-baseline">
                                    <span className="text-[10px] font-medium text-slate-400">UP Band</span>
                                    <span className="text-sm font-black dark:text-zinc-200">${selectedItem?.bb_upper?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-baseline border-y border-slate-100 dark:border-zinc-800/50 py-2">
                                    <span className="text-[10px] font-medium text-slate-400">Middle</span>
                                    <span className="text-sm font-black text-blue-500">${selectedItem?.bb_middle?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between items-baseline">
                                    <span className="text-[10px] font-medium text-slate-400">LOW Band</span>
                                    <span className="text-sm font-black dark:text-zinc-200">${selectedItem?.bb_lower?.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Moving Averages */}
                        <div className="bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md border border-slate-100 dark:border-zinc-800/50 p-5 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 transition-all">
                            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Activity className="h-3.5 w-3.5 text-emerald-400" /> Moving Averages
                            </div>
                            <div className="space-y-4">
                                <div className="flex items-center gap-4">
                                    <div className="h-8 w-1 bg-blue-500 rounded-full" />
                                    <div className="flex-1">
                                        <div className="text-[8px] font-bold text-slate-400 uppercase">MA 20 (Short)</div>
                                        <div className="text-sm font-black dark:text-zinc-100">${selectedItem?.ma_20?.toFixed(2)}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 opacity-70">
                                    <div className="h-8 w-1 bg-amber-500 rounded-full" />
                                    <div className="flex-1">
                                        <div className="text-[8px] font-bold text-slate-400 uppercase">MA 50 (Med)</div>
                                        <div className="text-sm font-black dark:text-zinc-100">${selectedItem?.ma_50?.toFixed(2)}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 opacity-40">
                                    <div className="h-8 w-1 bg-slate-500 rounded-full" />
                                    <div className="flex-1">
                                        <div className="text-[8px] font-bold text-slate-400 uppercase">MA 200 (Long)</div>
                                        <div className="text-sm font-black dark:text-zinc-100">${selectedItem?.ma_200?.toFixed(2)}</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Pivot Points & Volatility */}
                        <div className="bg-white/40 dark:bg-zinc-900/40 backdrop-blur-md border border-slate-100 dark:border-zinc-800/50 p-5 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 transition-all">
                             <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Target className="h-3.5 w-3.5 text-blue-400" /> Key Execution Levels
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-rose-500/5 p-3 rounded-2xl border border-rose-500/10">
                                    <div className="text-[8px] font-bold text-rose-400 uppercase mb-1">Resistance R1</div>
                                    <div className="text-sm font-black dark:text-rose-100 tabular-nums">${selectedItem?.resistance_1?.toFixed(2)}</div>
                                </div>
                                <div className="bg-emerald-500/5 p-3 rounded-2xl border border-emerald-500/10">
                                    <div className="text-[8px] font-bold text-emerald-400 uppercase mb-1">Support S1</div>
                                    <div className="text-sm font-black dark:text-emerald-100 tabular-nums">${selectedItem?.support_1?.toFixed(2)}</div>
                                </div>
                                <div className="col-span-2 bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 flex justify-between items-center">
                                    <div>
                                        <div className="text-[8px] font-bold text-blue-400 uppercase">Volatility (ATR 14)</div>
                                        <div className="text-sm font-black dark:text-blue-100 tabular-nums">${selectedItem?.atr_14?.toFixed(2)}</div>
                                    </div>
                                    <div className="px-2 py-1 rounded bg-blue-500/20 text-[8px] font-black text-blue-400 uppercase">Moderate</div>
                                </div>
                            </div>
                        </div>
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
                        { label: "市值", value: selectedItem?.market_cap ? (selectedItem.market_cap / 1e9).toFixed(1) + "B" : "-", sub: "Market Cap" },
                        { label: "市盈率", value: selectedItem?.pe_ratio?.toFixed(2) || "-", sub: "Trailing PE" },
                        { label: "预测市盈率", value: selectedItem?.forward_pe?.toFixed(2) || "-", sub: "Forward PE" },
                        { label: "每股收益", value: selectedItem?.eps?.toFixed(2) || "-", sub: "EPS" },
                        { label: "52周最高", value: "$" + (selectedItem?.fifty_two_week_high?.toFixed(2) || "-"), sub: "52W High" },
                        { label: "52周最低", value: "$" + (selectedItem?.fifty_two_week_low?.toFixed(2) || "-"), sub: "52W Low" },
                        { label: "板块", value: selectedItem?.sector || "-", sub: "Sector" },
                        { label: "细分行业", value: selectedItem?.industry || "-", sub: "Industry" },
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
