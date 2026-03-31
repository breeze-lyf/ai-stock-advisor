/**
 * 股票详情面板 - 编排层 (Stock Detail Panel - Orchestration Layer)
 * 职责：作为 L1 编排容器，负责：
 *   1. 管理全局状态（图层开关、滚动检测、数据加载）
 *   2. 协调数据请求（K 线历史、AI 分析历史）
 *   3. 将渲染职责委托给各板块子组件
 * 
 * 子组件层级：
 *   L2 板块组件：StickyBar / HeaderIdentity / MarketAnalysis / AIVerdict / TechnicalInsights / FundamentalCard / NewsFeed
 *   L3 原子组件：TradeAxis / SentimentBias / IndicatorCard 等（内嵌于 L2 中）
 */
"use client";

import React, { useState, useEffect, useRef } from "react";
import { Zap } from "lucide-react";
import { useDashboardStockDetailData } from "@/features/dashboard/hooks/useDashboardStockDetailData";
import { useAnalysisStatus } from "@/features/analysis/useAnalysisStatus";
import { PortfolioItem } from "@/types";
import { refreshStock } from "@/features/portfolio/api";
import { fetchStockHistory } from "@/features/market/api";
import type { AIData, AnalysisHistoryItem } from "./stock-detail/types";

// --- L2 板块子组件导入 ---
import { sanitizePrice, getCurrencySymbol } from "./stock-detail/shared";
import { StickyBar } from "./stock-detail/StickyBar";
import { HeaderIdentity } from "./stock-detail/HeaderIdentity";
import { MarketAnalysis } from "./stock-detail/MarketAnalysis";
import { AIVerdict } from "./stock-detail/AIVerdict";
import { PositionOverlay } from "./stock-detail/PositionOverlay";
import { TechnicalInsights } from "./stock-detail/TechnicalInsights";
import { FundamentalCard } from "./stock-detail/FundamentalCard";
import { NewsFeed } from "./stock-detail/NewsFeed";

// --- Types ---
interface HistoryDataItem {
    time: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
    [key: string]: unknown;
}

// --- Props 接口 ---
interface StockDetailProps {
    selectedItem: PortfolioItem | null;
    onAnalyze: (force?: boolean) => void;
    onRefresh: () => void;
    onBack?: () => void;
    analyzing: boolean;
    aiData: AIData | null;
    news?: Array<{ title?: string; url?: string; published_at?: string; source?: string; [key: string]: unknown }>;
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
    // --- 全局状态管理 ---
    const [refreshing, setRefreshing] = useState(false);
    const { analysisHistory, historyData, historyLoading } = useDashboardStockDetailData(
        selectedItem?.ticker || null,
        refreshTimestamp
    );

    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [mergedHistoryData, setMergedHistoryData] = useState<HistoryDataItem[]>([]);

    // --- 自动刷新通知 ---
    const { hasNewAnalysis, dismiss: dismissNewAnalysis } = useAnalysisStatus(
        selectedItem?.ticker ?? null,
        aiData?.created_at
    );

    // Reset merged data when ticker changes to prevent cross-ticker data bleed
    useEffect(() => {
        setMergedHistoryData([]);
    }, [selectedItem?.ticker]);

    // Sync merged history with initial history data while preserving manually loaded past history
    useEffect(() => {
        if (historyData && historyData.length > 0) {
            setMergedHistoryData((prev) => {
                // If it's a completely new ticker load (prev is empty)
                if (prev.length === 0) return historyData as HistoryDataItem[];
                
                // If the most recent data differs significantly, it might be a refresh.
                // We merge historyData (latest truth) into prev (existing history).
                const freshTimes = new Set((historyData as HistoryDataItem[]).map((d) => d.time));
                const historicalBase = prev.filter((d) => !freshTimes.has(d.time));
                return [...historicalBase, ...(historyData as HistoryDataItem[])].sort((a, b) => String(a.time).localeCompare(String(b.time)));
            });
        }
    }, [historyData]);

    useEffect(() => {
        if (!selectedItem?.ticker) return;
        if (Array.isArray(historyData) && historyData.length > 0 && mergedHistoryData.length === 0) {
            setMergedHistoryData(historyData as HistoryDataItem[]);
        }
    }, [historyData, mergedHistoryData.length, selectedItem?.ticker]);

    const handleLoadMore = async (earliestTime: string) => {
        if (!selectedItem || isLoadingMore) return;
        
        setIsLoadingMore(true);
        try {
            // Fetch 1 year more data ending at the current earliest time
            const moreData = await fetchStockHistory(selectedItem.ticker, "1y", earliestTime);
            
            if (Array.isArray(moreData) && moreData.length > 0) {
                setMergedHistoryData((prev) => {
                    const existingTimes = new Set(prev.map((d) => d.time));
                    const newItems = (moreData as HistoryDataItem[]).filter((item) => !existingTimes.has(item.time));
                    if (newItems.length === 0) return prev;
                    return [...newItems, ...prev].sort((a, b) => String(a.time).localeCompare(String(b.time)));
                });
            }
        } catch (err) {
            console.error("Failed to load more history:", err);
        } finally {
            setIsLoadingMore(false);
        }
    };

    // 图层切换开关
    const [showBb, setShowBb] = useState(true);
    const [showRsi, setShowRsi] = useState(false);
    const [showMacd, setShowMacd] = useState(false);

    // 滚动检测（触发粘性顶栏）
    const [isScrolled, setIsScrolled] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    const currency = selectedItem ? getCurrencySymbol(selectedItem.ticker) : "$";

    // --- 滚动检测 Effect ---
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const handleScroll = () => {
            setIsScrolled(container.scrollTop > 80);
        };

        container.addEventListener("scroll", handleScroll);
        container.scrollTop = 0;
        setIsScrolled(false);
        
        return () => container.removeEventListener("scroll", handleScroll);
    }, [selectedItem?.ticker]);

    // --- 空状态 ---
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

    // --- 刷新处理 ---
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

    // ===========================
    // 渲染：组装 5 大板块
    // ===========================
    return (
        <div 
            ref={containerRef}
            className="flex-1 bg-white dark:bg-zinc-950 px-4 md:px-8 pb-12 flex flex-col gap-6 md:gap-8 overflow-y-auto h-full custom-scrollbar w-full max-w-[1400px] mx-auto relative"
        >
            {/* 板块 0: 粘性顶栏（滚动后出现） */}
            <StickyBar
                selectedItem={selectedItem}
                isScrolled={isScrolled}
                refreshing={refreshing}
                onRefresh={handleRefresh}
                onBack={onBack}
                currency={currency}
                sanitizePrice={sanitizePrice}
            />

            {/* 板块 0: 股票身份头 */}
            <HeaderIdentity
                selectedItem={selectedItem}
                isScrolled={isScrolled}
                refreshing={refreshing}
                onRefresh={handleRefresh}
                onBack={onBack}
            />

            {/* 自动刷新通知 Banner */}
            {hasNewAnalysis && (
                <div
                    className="flex items-center justify-between mx-4 mt-3 px-4 py-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 cursor-pointer hover:bg-blue-500/20 transition-colors"
                    onClick={() => { dismissNewAnalysis(); onAnalyze(false); }}
                >
                    <div className="flex items-center gap-2 text-sm text-blue-400 font-medium">
                        <span className="animate-pulse">✦</span>
                        新版 AI 诊断已生成 · 点击查看
                    </div>
                    <button
                        onClick={(e) => { e.stopPropagation(); dismissNewAnalysis(); }}
                        className="text-blue-400/60 hover:text-blue-400 text-xs ml-3"
                    >
                        ✕
                    </button>
                </div>
            )}

            {/* 板块 1: 动态行情分析 */}
            <MarketAnalysis
                historyData={mergedHistoryData}
                ticker={selectedItem.ticker}
                showBb={showBb}
                showRsi={showRsi}
                showMacd={showMacd}
                onToggleBb={() => setShowBb(!showBb)}
                onToggleRsi={() => setShowRsi(!showRsi)}
                onToggleMacd={() => setShowMacd(!showMacd)}
                onLoadMore={handleLoadMore}
                isLoadingMore={isLoadingMore}
                isLoading={historyLoading}
            />

            {/* 板块 2: AI 智能判研指标 */}
            <AIVerdict
                selectedItem={selectedItem}
                aiData={aiData}
                analysisHistory={analysisHistory as AnalysisHistoryItem[]}
                analyzing={analyzing}
                onAnalyze={onAnalyze}
                currency={currency}
                sanitizePrice={sanitizePrice}
            />

            <PositionOverlay
                selectedItem={selectedItem}
                aiData={aiData}
                currency={currency}
                sanitizePrice={sanitizePrice}
            />

            {/* 板块 3: 技术面深度透视 */}
            <TechnicalInsights
                selectedItem={selectedItem}
                aiData={aiData}
                analyzing={analyzing}
            />

            {/* 板块 4: 基本面资料卡 */}
            <FundamentalCard
                selectedItem={selectedItem}
                aiData={aiData}
            />

            {/* 板块 5: 实时资讯流 */}
            <NewsFeed news={news} aiData={aiData} />

            {/* Footer */}
            <div className="mt-8 py-4 border-t border-slate-100 dark:border-slate-800 text-center opacity-30">
                <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.3em]">AI Analysis Terminal V4.0</p>
            </div>
        </div>
    );
}
