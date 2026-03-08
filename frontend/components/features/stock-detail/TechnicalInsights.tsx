/**
 * 技术面深度透视板块 (Technical Insights Section)
 * 职责：展示 6 个技术指标卡片矩阵 + AI 智能分析结论
 * 包含：均线系统、MACD 趋势动量、RSI/KDJ、关键执行位、布林带轨道、估值资金流
 * 布局规范：标题已顶格，内容含内部 padding
 */
"use client";

import React from "react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import {
    TrendingUp, Target, Activity,
    LineChart, PieChart, Zap
} from "lucide-react";
import { TechnicalInsightsProps } from "./types";
import { ReferenceCitation, getRSIColor } from "./shared";

export const TechnicalInsights = React.memo(function TechnicalInsights({
    selectedItem,
    aiData,
    analyzing
}: TechnicalInsightsProps) {
    return (
        <div className="space-y-4 relative">
            {/* 标题栏：顶格对齐 */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.5)]" />
                    <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-zinc-100 uppercase">技术面深度透视</h2>
                </div>
            </div>

            {/* Dashboard Background & Grid Overlay */}
            <div className="absolute inset-0 -z-10 bg-slate-100/40 dark:bg-zinc-900/40 rounded-[40px] pointer-events-none overflow-hidden border border-slate-200 dark:border-zinc-800/50">
                <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]" 
                     style={{ backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
                <div className="absolute top-0 left-1/4 w-1/2 h-1/2 bg-blue-500/5 dark:bg-blue-400/5 blur-[120px] rounded-full" />
                <div className="absolute bottom-0 right-1/4 w-1/2 h-1/2 bg-emerald-500/5 dark:bg-emerald-400/5 blur-[120px] rounded-full" />
            </div>

            <div className="px-4 md:px-8 py-2 md:py-3 space-y-6">

                {/* Row 1: Core Foundations (均线、MACD、RSI/KDJ) */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* 均线系统卡片 */}
                    <div id="REF_T1" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-emerald-500/20 hover:shadow-lg transition-all shadow-md flex flex-col justify-between scroll-mt-24">
                        <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                <LineChart className="h-4 w-4 text-emerald-400" /> 均线系统
                            </span>
                        </div>
                        <div className="space-y-3">
                            <div className="flex items-center gap-3">
                                <div className="h-6 w-1 bg-blue-500 rounded-full" />
                                <div className="flex-1">
                                    <div className="text-[8px] font-bold text-slate-400 uppercase">MA 20 (Short)</div>
                                    <div className="text-xs font-black dark:text-zinc-100 tabular-nums">${selectedItem?.ma_20?.toFixed(2)}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 opacity-70">
                                <div className="h-6 w-1 bg-amber-500 rounded-full" />
                                <div className="flex-1">
                                    <div className="text-[8px] font-bold text-slate-400 uppercase">MA 50 (Med)</div>
                                    <div className="text-xs font-black dark:text-zinc-100 tabular-nums">${selectedItem?.ma_50?.toFixed(2)}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 opacity-40">
                                <div className="h-6 w-1 bg-slate-500 rounded-full" />
                                <div className="flex-1">
                                    <div className="text-[8px] font-bold text-slate-400 uppercase">MA 200 (Long)</div>
                                    <div className="text-xs font-black dark:text-zinc-100 tabular-nums">${selectedItem?.ma_200?.toFixed(2)}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* MACD 趋势动量卡片 */}
                    <div id="REF_T2" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-indigo-500/30 hover:shadow-lg transition-all shadow-md flex flex-col justify-between overflow-hidden relative group scroll-mt-24">
                        <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                <Activity className="h-4 w-4 text-indigo-500" /> MACD 趋势动量
                            </span>
                            <span className={clsx(
                                "text-[9px] font-black px-2 py-0.5 rounded-full uppercase",
                                selectedItem?.macd_cross === "GOLDEN" ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
                            )}>
                                {selectedItem?.macd_cross === "GOLDEN" ? "金叉" : "死叉"}
                            </span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-x-6 gap-y-3 relative z-10">
                            <div className="space-y-1">
                                <div className="text-[7px] font-bold text-slate-400 uppercase">DIF / DEA</div>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-xs font-black tabular-nums">{selectedItem?.macd_val?.toFixed(2)}</span>
                                    <span className="text-[10px] text-slate-400 tabular-nums">{selectedItem?.macd_signal?.toFixed(2)}</span>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[7px] font-bold text-slate-400 uppercase">柱状值 / 斜率</div>
                                <div className="flex items-baseline gap-2">
                                    <span className={clsx("text-xs font-black tabular-nums", (selectedItem?.macd_hist || 0) >= 0 ? "text-emerald-500" : "text-rose-500")}>
                                        {selectedItem?.macd_hist?.toFixed(2)}
                                    </span>
                                    <span className={clsx("text-[9px] font-bold", (selectedItem?.macd_hist_slope || 0) >= 0 ? "text-emerald-400" : "text-rose-400")}>
                                        {(selectedItem?.macd_hist_slope || 0) > 0 ? "↑" : "↓"}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Mini MACD Visualizer */}
                        <div className="absolute bottom-0 left-0 w-full h-8 flex items-end gap-[1px] px-1 opacity-20 group-hover:opacity-40 transition-opacity">
                            {[...Array(24)].map((_, i) => {
                                const h = Math.random() * 20 + 5;
                                const isPos = Math.random() > 0.4;
                                return (
                                    <div 
                                        key={i} 
                                        className={clsx("flex-1 rounded-t-sm", isPos ? "bg-emerald-400" : "bg-rose-400")} 
                                        style={{ height: `${h}px` }}
                                    />
                                );
                            })}
                        </div>
                    </div>

                    {/* RSI & KDJ 卡片 */}
                    <div id="REF_T3" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-blue-500/30 hover:shadow-lg transition-all group shadow-md flex flex-col justify-between scroll-mt-24">
                        <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                <TrendingUp className="h-4 w-4 text-blue-500" /> 强弱指标 (RSI/KDJ)
                            </span>
                            <span className="text-xl font-black tabular-nums text-blue-500">{selectedItem?.rsi_14?.toFixed(2)}</span>
                        </div>
                        
                        <div className="space-y-3">
                            <div className="relative h-1.5 w-full bg-slate-100 dark:bg-zinc-800/80 rounded-full overflow-hidden">
                                <div className="absolute left-[20%] top-0 h-full w-px bg-slate-200 dark:bg-zinc-700 z-10" />
                                <div className="absolute left-[80%] top-0 h-full w-px bg-slate-200 dark:bg-zinc-700 z-10" />
                                <div
                                    className={clsx("h-full rounded-full transition-all duration-1000", getRSIColor(selectedItem?.rsi_14 || 50))}
                                    style={{ width: `${selectedItem?.rsi_14 || 0}%` }}
                                />
                            </div>
                            <div className="flex justify-between text-[7px] font-bold text-slate-400 uppercase tracking-widest px-1">
                                <span>Oversold</span>
                                <span>Overbought</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-slate-50 dark:border-zinc-800/50">
                            <div className="flex items-center gap-3">
                                <span className="text-[9px] font-bold text-blue-400">K {selectedItem?.k_line?.toFixed(0)}</span>
                                <span className="text-[9px] font-bold text-amber-400">D {selectedItem?.d_line?.toFixed(0)}</span>
                                <span className={clsx("text-[9px] font-black", (selectedItem?.j_line || 0) > 80 ? "text-rose-400" : "text-emerald-400")}>
                                    J {selectedItem?.j_line?.toFixed(0)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Row 2: Execution & Auxiliary (关键执行位、布林带、估值资金流) */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* 关键执行位卡片 */}
                    <div id="REF_T4" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-blue-500/20 hover:shadow-lg transition-all shadow-md flex flex-col justify-between scroll-mt-24">
                         <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                <Target className="h-4 w-4 text-blue-400" /> 关键执行位
                            </span>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-rose-500/5 p-2.5 rounded-xl border border-rose-500/10">
                                <div className="text-[7px] font-bold text-rose-400 uppercase mb-0.5">阻力位 R1</div>
                                <div className="text-xs font-black dark:text-rose-100 tabular-nums">${selectedItem?.resistance_1?.toFixed(2)}</div>
                            </div>
                            <div className="bg-emerald-500/5 p-2.5 rounded-xl border border-emerald-500/10">
                                <div className="text-[7px] font-bold text-emerald-400 uppercase mb-0.5">支撑位 S1</div>
                                <div className="text-xs font-black dark:text-emerald-100 tabular-nums">${selectedItem?.support_1?.toFixed(2)}</div>
                            </div>
                            <div className="col-span-2 bg-blue-500/5 p-2.5 rounded-xl border border-blue-500/10 flex justify-between items-center">
                                <div className="flex flex-col">
                                    <div className="text-[7px] font-bold text-blue-400 uppercase">平均振幅 ATR</div>
                                    <div className="text-xs font-black dark:text-blue-100 tabular-nums">${selectedItem?.atr_14?.toFixed(2)}</div>
                                </div>
                                <div className="px-1.5 py-0.5 rounded bg-blue-500/20 text-[7px] font-black text-blue-400 uppercase">Moderate</div>
                            </div>
                        </div>
                    </div>

                    {/* 布林带轨道卡片 */}
                    <div id="REF_T5" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-rose-500/20 hover:shadow-lg transition-all flex flex-col shadow-md space-y-3 scroll-mt-24">
                        <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                <Zap className="h-4 w-4 text-rose-400" /> 布林带轨道
                            </span>
                        </div>
                        
                        <div className="flex-1 flex gap-4 items-center">
                            <div className="relative h-20 w-1 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden shrink-0">
                                <div className="absolute top-1/2 left-0 w-full h-0.5 bg-blue-500/30 -translate-y-1/2" />
                                {(() => {
                                    const upper = selectedItem?.bb_upper || 0;
                                    const lower = selectedItem?.bb_lower || 0;
                                    const current = selectedItem?.price || selectedItem?.current_price || 0;
                                    const range = upper - lower;
                                    if (range <= 0 || current <= 0) return null;
                                    let pos = ((current - lower) / range) * 100;
                                    const clampedPos = Math.max(-5, Math.min(105, pos)); 
                                    return (
                                        <div 
                                            className={clsx(
                                                "absolute left-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-zinc-900 shadow-sm z-10 transition-all duration-500",
                                                pos > 90 ? "bg-rose-500" : 
                                                pos < 10 ? "bg-emerald-500" : "bg-blue-500"
                                            )}
                                            style={{ bottom: `${clampedPos}%` }}
                                        />
                                    );
                                })()}
                                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-emerald-500/20 via-blue-500/10 to-rose-500/20 w-full h-full" />
                            </div>

                            <div className="flex-1 space-y-1.5">
                                <div className="flex justify-between items-center group">
                                    <span className="text-[9px] font-medium text-slate-400 uppercase">Upper</span>
                                    <span className="text-[10px] font-black dark:text-zinc-200 tabular-nums">${selectedItem?.bb_upper?.toFixed(2) || "0.00"}</span>
                                </div>
                                <div className="flex justify-between items-center py-1 border-y border-slate-50 dark:border-zinc-800/50 px-1 rounded transition-colors group">
                                    <span className="text-[9px] font-bold text-blue-500 uppercase">Mid</span>
                                    <span className="text-[10px] font-black text-blue-500 tabular-nums">${selectedItem?.bb_middle?.toFixed(2) || "0.00"}</span>
                                </div>
                                <div className="flex justify-between items-center group">
                                    <span className="text-[9px] font-medium text-slate-400 uppercase">Lower</span>
                                    <span className="text-[10px] font-black dark:text-zinc-200 tabular-nums">${selectedItem?.bb_lower?.toFixed(2) || "0.00"}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 估值与资金流卡片 */}
                    <div id="REF_V1" className="bg-white dark:bg-zinc-900/40 backdrop-blur-md border border-slate-200 dark:border-zinc-800/50 p-4 rounded-3xl space-y-4 hover:bg-white/60 dark:hover:bg-zinc-800/40 hover:border-emerald-500/30 hover:shadow-lg transition-all group shadow-md flex flex-col justify-between relative overflow-hidden scroll-mt-24">
                        <div className="flex justify-between items-center h-8 mb-2 relative z-10">
                            <span className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 tracking-[0.2em] flex items-center gap-2">
                                <PieChart className="h-4 w-4 text-emerald-500" /> 估值与资金流
                            </span>
                            <div className="px-2 py-0.5 rounded bg-emerald-500/10 text-[9px] font-black text-emerald-500 tabular-nums">
                                {selectedItem?.net_inflow ? `${(selectedItem.net_inflow / 10000).toFixed(0)}w` : "--"}
                            </div>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 relative z-10">
                            <div className="space-y-2">
                                <div className="flex justify-between text-[8px] font-black text-slate-500">
                                    <span>市盈率 PE</span>
                                    <span>{selectedItem?.pe_percentile?.toFixed(0)}%</span>
                                </div>
                                <div className="relative h-1.5 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500/60 transition-all duration-700" style={{ width: `${selectedItem?.pe_percentile || 0}%` }} />
                                </div>
                                <p className="text-[6px] text-slate-400 uppercase">Percentile</p>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between text-[8px] font-black text-slate-500">
                                    <span>市净率 PB</span>
                                    <span>{selectedItem?.pb_percentile?.toFixed(0)}%</span>
                                </div>
                                <div className="relative h-1.5 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="h-full bg-blue-500/60 transition-all duration-700" style={{ width: `${selectedItem?.pb_percentile || 0}%` }} />
                                </div>
                                <p className="text-[6px] text-slate-400 uppercase">Percentile</p>
                            </div>
                        </div>

                        {/* Decorative Grid Pattern */}
                        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
                             style={{ backgroundImage: 'radial-gradient(#10b981 0.5px, transparent 0.5px)', backgroundSize: '10px 10px' }} />
                    </div>
                </div>

                {/* AI 技术分析结论 - 极简双列分栏卡片 */}
                <div className="mt-4 bg-slate-50/80 dark:bg-zinc-800/20 border border-slate-200/50 dark:border-zinc-800/50 rounded-2xl p-4 md:p-5 flex flex-col md:flex-row gap-4 items-start">
                    {/* 侧边标题 */}
                    <div className="flex items-center gap-2 shrink-0 md:w-28 md:pt-1">
                        <div className="h-3 w-1 bg-blue-500 rounded-full shrink-0" />
                        <h3 className="text-[10px] font-black uppercase text-slate-500 dark:text-zinc-400 tracking-[0.2em] whitespace-nowrap">AI 深度分析</h3>
                    </div>

                    <div className="flex-1 min-w-0 md:border-l border-slate-200/50 dark:border-zinc-800/50 md:pl-5">
                        {analyzing ? (
                            <div className="flex items-center justify-center h-full gap-3 py-4 text-slate-400 dark:text-zinc-500">
                                <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                                <p className="text-[9px] font-bold tracking-widest uppercase">模型研判中...</p>
                            </div>
                        ) : aiData?.technical_analysis ? (
                            <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                                <div className="text-[12px] leading-snug text-slate-600 dark:text-zinc-400">
                                    <ReactMarkdown
                                        components={{
                                            h3: ({ node, ...props }) => (
                                                <h3 className="font-bold text-blue-500 dark:text-blue-400 mt-4 mb-2 first:mt-0 text-sm block">
                                                    {props.children}
                                                </h3>
                                            ),
                                            h4: ({ node, ...props }) => (
                                                <h4 className="font-bold text-blue-500 dark:text-blue-400 mt-3 mb-1 first:mt-0 text-sm block">
                                                    {props.children}
                                                </h4>
                                            ),
                                            strong: ({ node, ...props }) => (
                                                <strong className="font-bold text-blue-500 dark:text-blue-400">
                                                    {props.children}
                                                </strong>
                                            ),
                                            ul: ({ node, ...props }) => (
                                                <ul className="list-disc pl-4 mt-0 mb-4 space-y-2 last:mb-0 text-slate-600 dark:text-zinc-400 block w-full">
                                                    {props.children}
                                                </ul>
                                            ),
                                            ol: ({ node, ...props }) => (
                                                <ol className="list-decimal pl-4 mt-0 mb-4 space-y-2 last:mb-0 text-slate-600 dark:text-zinc-400 block w-full">
                                                    {props.children}
                                                </ol>
                                            ),
                                            li: ({ node, ...props }) => (
                                                <li className="m-0 p-0">
                                                    {props.children}
                                                </li>
                                            ),
                                            p: ({ node, ...props }) => {
                                                const children = React.Children.toArray(props.children);
                                                return (
                                                    <p className="mt-0 mb-2 last:mb-0 block w-full">
                                                        {children}
                                                    </p>
                                                );
                                            }
                                        }}
                                    >
                                        {(aiData.technical_analysis?.replace(/\[\[REF_[A-Z0-9]+\]\]/g, '') || '').replace(/([。！？；;：:\.!\?])\s+(\*\*.*?\*\*\s*[:：])/g, '$1\n\n$2')}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full py-4 text-slate-300 dark:text-zinc-600">
                                <p className="text-[9px] font-bold uppercase tracking-widest">暂无分析信号</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
});
