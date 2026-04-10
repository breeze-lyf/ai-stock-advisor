/**
 * 基本面资料卡板块 (Fundamental Data Card)
 * 职责：展示 8 项核心基本面数据（市值、PE、EPS 等）+ 消息面综述
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { FundamentalCardProps } from "./types";

export const FundamentalCard = React.memo(function FundamentalCard({
    selectedItem,
    fundamentalCapsule,
    fundamentalCapsuleUpdatedAt,
    onRefreshCapsule,
    refreshingCapsule,
}: FundamentalCardProps) {
    return (
        <div className="space-y-8">
            {/* 标题栏：顶格对齐 */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-amber-500 rounded-full shadow-[0_0_12px_rgba(245,158,11,0.5)]" />
                    <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">基本面资料卡</h2>
                </div>
                {onRefreshCapsule && (
                    <button
                        onClick={onRefreshCapsule}
                        disabled={refreshingCapsule}
                        className="text-[10px] font-black uppercase tracking-widest text-amber-500 hover:text-amber-600 disabled:opacity-40 transition-colors"
                    >
                        {refreshingCapsule ? "生成中…" : "↺ 刷新摘要"}
                    </button>
                )}
            </div>

            {/* 内容区：缩进 */}
            <div className="px-4 md:px-10">
                {/* 8 项基本面数据网格 */}
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

                {/* 预计算 AI 基本面摘要 (Capsule) — 优先于全量分析中的 fundamental_analysis */}
                {fundamentalCapsule && (
                    <div className="mt-8">
                        <div className="bg-amber-50/60 dark:bg-amber-900/10 border border-amber-200/40 dark:border-amber-800/30 rounded-2xl p-4 md:p-5 flex flex-col md:flex-row gap-4 items-start">
                            <div className="flex items-center gap-2 shrink-0 md:w-28 md:pt-1">
                                <div className="h-3 w-1 bg-amber-500 rounded-full shrink-0" />
                                <h3 className="text-[10px] font-black uppercase text-amber-600 dark:text-amber-400 tracking-[0.2em] whitespace-nowrap">AI 基本面摘要</h3>
                            </div>
                            <div className="flex-1 min-w-0 md:border-l border-amber-200/40 dark:border-amber-800/30 md:pl-5">
                                <div className="prose prose-sm prose-slate dark:prose-invert max-w-none text-[12px] leading-snug text-slate-600 dark:text-zinc-400">
                                    <ReactMarkdown>{fundamentalCapsule}</ReactMarkdown>
                                </div>
                                {fundamentalCapsuleUpdatedAt && (
                                    <p className="mt-3 text-[10px] text-slate-400 dark:text-zinc-500">
                                        摘要更新: {new Date(fundamentalCapsuleUpdatedAt).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>
                )}


            </div>
        </div>
    );
});
