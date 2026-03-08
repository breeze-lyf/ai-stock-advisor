/**
 * 基本面资料卡板块 (Fundamental Data Card)
 * 职责：展示 8 项核心基本面数据（市值、PE、EPS 等）+ 消息面综述
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Activity } from "lucide-react";
import { FundamentalCardProps } from "./types";
import { ReferenceCitation } from "./shared";

export const FundamentalCard = React.memo(function FundamentalCard({
    selectedItem,
    aiData
}: FundamentalCardProps) {
    return (
        <div className="space-y-8">
            {/* 标题栏：顶格对齐 */}
            <div className="flex items-center gap-3">
                <div className="h-8 w-1.5 bg-amber-500 rounded-full shadow-[0_0_12px_rgba(245,158,11,0.5)]" />
                <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">基本面资料卡</h2>
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

                {/* 消息面综述 (Moved to NewsFeed) */}
            </div>
        </div>
    );
});
