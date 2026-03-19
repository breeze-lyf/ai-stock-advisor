/**
 * 动态行情分析板块 (Market Analysis Section)
 * 职责：展示 K 线图 + 图层切换控制（布林带/RSI/MACD）
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import clsx from "clsx";
import { Settings2 } from "lucide-react";
import { StockChart } from "../StockChart";
import { MarketAnalysisProps } from "./types";

export const MarketAnalysis = React.memo(function MarketAnalysis({
    historyData,
    ticker,
    showBb,
    showRsi,
    showMacd,
    onToggleBb,
    onToggleRsi,
    onToggleMacd
}: MarketAnalysisProps) {
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
                    <StockChart 
                        key={ticker}
                        data={historyData} 
                        ticker={ticker} 
                        showBb={showBb}
                        showRsi={showRsi} 
                        showMacd={showMacd} 
                    />
                </div>
            </div>
        </div>
    );
});
