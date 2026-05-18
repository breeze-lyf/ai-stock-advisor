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
import { getPositionImpactAnalysis, type PositionImpactAnalysis } from "@/features/portfolio/risk-api";
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
import { ScenarioAnalysis } from "./stock-detail/ScenarioAnalysis";
import { RiskAnalysis } from "./stock-detail/RiskAnalysis";
import { MultiTimeframeAnalysis } from "./stock-detail/MultiTimeframeAnalysis";
import { KeyAssumptions } from "./stock-detail/KeyAssumptions";
import { CatalystTimeline } from "./stock-detail/CatalystTimeline";

// --- 增强分析 Hook ---
import { useEnhancedAnalysis } from "@/features/analysis/hooks/useEnhancedAnalysis";
// --- 预计算摘要 Hook ---
import { useStockCapsule } from "@/features/dashboard/hooks/useStockCapsule";

type DetailTab = "info" | "analysis";

function resolveDetailTab(
    requestedTab: DetailTab,
    detailTabStorageKey: string | null,
): DetailTab {
    if (requestedTab === "analysis") {
        return "analysis";
    }

    if (typeof window === "undefined") {
        return requestedTab;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("detail") === "analysis") {
        return "analysis";
    }

    if (detailTabStorageKey && window.sessionStorage.getItem(detailTabStorageKey) === "analysis") {
        return "analysis";
    }

    return "info";
}

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
    activeTab: DetailTab;
    onTabChange?: (tab: DetailTab) => void;
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
    activeTab,
    onTabChange,
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
    const [positionImpact, setPositionImpact] = useState<PositionImpactAnalysis | null>(null);
    const { analysisHistory, historyData, stockHistoryLoading } = useDashboardStockDetailData(
        selectedItem?.ticker || null,
        refreshTimestamp
    );

    // --- 增强分析数据 ---
    const enhancedAnalysis = useEnhancedAnalysis(selectedItem?.ticker || null);

    // --- 预计算摘要 (StockCapsule) ---
    const { newsCapsule, fundamentalCapsule, technicalCapsule, refresh: refreshCapsule, refreshing: refreshingCapsule } = useStockCapsule(selectedItem?.ticker || null);

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

    useEffect(() => {
        const ticker = selectedItem?.ticker;
        const positionPct = aiData?.max_position_pct;

        if (!ticker || positionPct == null) {
            setPositionImpact(null);
            return;
        }

        let cancelled = false;

        const loadPositionImpact = async () => {
            try {
                const result = await getPositionImpactAnalysis(ticker, positionPct);
                if (!cancelled) {
                    setPositionImpact(result);
                }
            } catch (err) {
                console.error("Failed to load portfolio linkage:", err);
                if (!cancelled) {
                    setPositionImpact(null);
                }
            }
        };

        void loadPositionImpact();

        return () => {
            cancelled = true;
        };
    }, [selectedItem?.ticker, aiData?.max_position_pct]);

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
    const detailTabStorageKey = selectedItem ? `stock-detail-tab:${selectedItem.ticker}` : null;
    const [resolvedActiveTab, setResolvedActiveTab] = useState<DetailTab>(() =>
        resolveDetailTab(activeTab, detailTabStorageKey)
    );

    useEffect(() => {
        setResolvedActiveTab(resolveDetailTab(activeTab, detailTabStorageKey));
    }, [activeTab, detailTabStorageKey]);

    useEffect(() => {
        if (typeof window === "undefined" || !detailTabStorageKey) return;
        window.sessionStorage.setItem(detailTabStorageKey, resolvedActiveTab);
    }, [detailTabStorageKey, resolvedActiveTab]);

    useEffect(() => {
        if (typeof onTabChange === "function" && resolvedActiveTab !== activeTab) {
            onTabChange(resolvedActiveTab);
        }
    }, [activeTab, onTabChange, resolvedActiveTab]);

    useEffect(() => {
        if (typeof window === "undefined") return;

        const params = new URLSearchParams(window.location.search);
        const urlDetailTab: DetailTab = params.get("detail") === "analysis" ? "analysis" : "info";
        if (urlDetailTab === resolvedActiveTab) {
            return;
        }

        if (resolvedActiveTab === "analysis") {
            params.set("detail", "analysis");
        } else {
            params.delete("detail");
        }

        const nextQuery = params.toString();
        const nextUrl = nextQuery ? `${window.location.pathname}?${nextQuery}` : window.location.pathname;
        window.history.replaceState(window.history.state, "", nextUrl);
    }, [resolvedActiveTab]);

    const handleDetailTabChange = (nextTab: DetailTab) => {
        setResolvedActiveTab(nextTab);
        onTabChange?.(nextTab);
    };

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
    // mounted pattern: ensures server/client render the same tree on first pass,
    // avoiding hydration mismatch when selectedItem is only available client-side
    const [mounted, setMounted] = React.useState(false);
    React.useEffect(() => setMounted(true), []);

    if (!mounted || !selectedItem) {
        return (
            <div className="flex-1 bg-slate-50 dark:bg-zinc-950 p-6 flex flex-col items-center justify-center h-full text-slate-300 gap-4">
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
            className="flex-1 bg-slate-50 dark:bg-zinc-950 px-4 md:px-8 pb-2 md:pb-4 flex flex-col gap-5 md:gap-6 overflow-y-auto h-full custom-scrollbar w-full max-w-[1400px] mx-auto relative"
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
                activeTab={resolvedActiveTab}
                onTabChange={handleDetailTabChange}
            />

            {/* 板块 0: 股票身份头 */}
            <HeaderIdentity
                selectedItem={selectedItem}
                isScrolled={isScrolled}
                refreshing={refreshing}
                onRefresh={handleRefresh}
                onBack={onBack}
                activeTab={resolvedActiveTab}
                onTabChange={handleDetailTabChange}
            />

            {/* 自动刷新通知 Banner */}
            {hasNewAnalysis && (
                <div
                    className="flex items-center justify-between mx-4 mt-3 px-4 py-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 cursor-pointer hover:bg-blue-500/20 transition-colors"
                    onClick={() => { dismissNewAnalysis(); handleDetailTabChange("analysis"); onAnalyze(false); }}
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



            {/* === 标的信息 Tab === */}
            {resolvedActiveTab === "info" && (
              <>
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
                isLoading={stockHistoryLoading}
            />

            {/* 板块 3: 技术面深度透视 */}
            <TechnicalInsights
                selectedItem={selectedItem}
                technicalCapsule={technicalCapsule?.content}
                technicalCapsuleUpdatedAt={technicalCapsule?.updated_at ?? null}
                onRefreshCapsule={refreshCapsule}
                refreshingCapsule={refreshingCapsule}
            />

            {/* 板块 4: 基本面资料卡 */}
            <FundamentalCard
                selectedItem={selectedItem}
                fundamentalCapsule={fundamentalCapsule?.content}
                fundamentalCapsuleUpdatedAt={fundamentalCapsule?.updated_at ?? null}
                onRefreshCapsule={refreshCapsule}
                refreshingCapsule={refreshingCapsule}
            />

            {/* 板块 5: 实时资讯流 */}
            <NewsFeed
              news={news}
              aiData={aiData}
              newsCapsule={newsCapsule?.content}
              newsCapsuleUpdatedAt={newsCapsule?.updated_at ?? null}
              onRefreshCapsule={refreshCapsule}
              refreshingCapsule={refreshingCapsule}
            />
              </>
            )}

            {/* === AI 分析 Tab === */}
            {resolvedActiveTab === "analysis" && (
              <>
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
                positionImpact={positionImpact}
            />

            {/* 关键假设断点 */}
            <KeyAssumptions assumptions={aiData?.key_assumptions} />

            {/* 催化剂时间轴 */}
            <CatalystTimeline catalysts={aiData?.catalysts} />

            {/* 增强分析模块 */}
            {enhancedAnalysis.data && (
                <>
                    {enhancedAnalysis.data.scenario_analysis && (
                        <ScenarioAnalysis
                            ticker={selectedItem?.ticker || ""}
                            scenarioAnalysis={enhancedAnalysis.data.scenario_analysis}
                            loading={enhancedAnalysis.loading === "scenario" || enhancedAnalysis.loading === "all"}
                        />
                    )}
                    {enhancedAnalysis.data.risk_analysis && (
                        <RiskAnalysis
                            ticker={selectedItem?.ticker || ""}
                            riskAnalysis={enhancedAnalysis.data.risk_analysis}
                            loading={enhancedAnalysis.loading === "risk" || enhancedAnalysis.loading === "all"}
                        />
                    )}
                    {enhancedAnalysis.data.multi_timeframe && (
                        <MultiTimeframeAnalysis
                            ticker={selectedItem?.ticker || ""}
                            analysis={enhancedAnalysis.data.multi_timeframe}
                            loading={enhancedAnalysis.loading === "timeframe" || enhancedAnalysis.loading === "all"}
                        />
                    )}
                </>
            )}

              </>
            )}

        </div>
    );
}
