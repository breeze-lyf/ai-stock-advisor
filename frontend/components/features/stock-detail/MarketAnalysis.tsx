/**
 * 动态行情分析板块 (Market Analysis Section)
 * 职责：展示 K 线图 + 图层切换控制（布林带/RSI/MACD）
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import clsx from "clsx";
import { Settings2 } from "lucide-react";
import { StockChart, type ChartDataPoint } from "../StockChart";
import { MarketAnalysisProps } from "./types";

export const MarketAnalysis = React.memo(function MarketAnalysis({
    historyData,
    ticker,
    showBb,
    showRsi,
    showMacd,
    onToggleBb,
    onToggleRsi,
    onToggleMacd,
    onLoadMore,
    isLoadingMore,
    isLoading = false
}: MarketAnalysisProps) {
    const hasData = historyData && historyData.length > 0;
    const chartData: ChartDataPoint[] = historyData
        .filter(
            (item) =>
                typeof item.time === "string" &&
                typeof item.open === "number" &&
                typeof item.high === "number" &&
                typeof item.low === "number" &&
                typeof item.close === "number"
        )
        .map((item) => ({
            time: item.time,
            open: item.open as number,
            high: item.high as number,
            low: item.low as number,
            close: item.close as number,
            volume: typeof item.volume === "number" ? item.volume : undefined,
            bb_upper: typeof item.bb_upper === "number" ? item.bb_upper : undefined,
            bb_middle: typeof item.bb_middle === "number" ? item.bb_middle : undefined,
            bb_lower: typeof item.bb_lower === "number" ? item.bb_lower : undefined,
            rsi: typeof item.rsi === "number" ? item.rsi : undefined,
            macd: typeof item.macd === "number" ? item.macd : undefined,
            macd_signal: typeof item.macd_signal === "number" ? item.macd_signal : undefined,
            macd_hist: typeof item.macd_hist === "number" ? item.macd_hist : undefined,
        }));

    return (
        <div className="space-y-8">
            <div className="flex flex-col gap-4">
                {/* 标题栏：顶格对齐，不使用水平缩进 */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-1.5 bg-emerald-600 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.5)]" />
                        <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">动态行情分析</h2>
                    </div>
                    
                    <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800/50 p-1 rounded-xl mr-4 md:mr-10">
                        <div className="px-3 py-1.5 text-[9px] font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                            <Settings2 className="h-3 w-3" /> 图层控制
                        </div>
                        <button
                            onClick={onToggleBb}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                showBb ? "bg-slate-700 text-white shadow-md" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            )}
                        >
                            BB
                        </button>
                        <button
                            onClick={onToggleRsi}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                showRsi ? "bg-blue-600 text-white shadow-md shadow-blue-600/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            )}
                        >
                            RSI
                        </button>
                        <button
                            onClick={onToggleMacd}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-[9px] font-black uppercase transition-all duration-200",
                                showMacd ? "bg-indigo-500 text-white shadow-md shadow-indigo-500/20" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            )}
                        >
                            MACD
                        </button>
                    </div>
                </div>
                
                {/* 内容区：保持缩进 */}
                <div className="relative group px-4 md:px-10">
                    {isLoading && !hasData ? (
                        <div className="w-full h-[400px] bg-white dark:bg-slate-900 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 p-2 flex items-center justify-center">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">加载行情数据中...</span>
                            </div>
                        </div>
                    ) : !hasData ? (
                        <div className="w-full h-[400px] bg-white dark:bg-slate-900 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 p-2 flex items-center justify-center">
                            <div className="flex flex-col items-center gap-3 opacity-40">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">No Data Available</span>
                                <span className="text-[9px] text-slate-400 text-center max-w-[200px]">暂无历史行情数据，请检查网络连接或稍后重试</span>
                            </div>
                        </div>
                    ) : (
                        <StockChart 
                            key={ticker}
                            data={chartData}
                            ticker={ticker} 
                            showBb={showBb}
                            showRsi={showRsi} 
                            showMacd={showMacd} 
                            onLoadMore={onLoadMore}
                            isLoadingMore={isLoadingMore}
                        />
                    )}
                </div>
            </div>
        </div>
    );
});
