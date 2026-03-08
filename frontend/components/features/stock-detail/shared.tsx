/**
 * 共享工具函数与微型组件 (Shared Utilities & Micro-Components)
 * 职责：提供跨板块复用的工具函数、Markdown 渲染器、引用标签等
 */
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Link2 } from "lucide-react";

// ========================================
// 工具函数 (Utility Functions)
// ========================================

/** 价格清洗：将 null/undefined/NaN 统一渲染为 "--" */
export const sanitizePrice = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isNaN(val)) return "--";
    return val.toFixed(2);
};

/** 根据 ticker 后缀判断货币符号 */
export const getCurrencySymbol = (ticker: string): string => {
    const isCN = /^\d{6}/.test(ticker) || ticker.toUpperCase().endsWith('.SS') || ticker.toUpperCase().endsWith('.SZ');
    return isCN ? "¥" : "$";
};

/** RSI 进度条颜色：超买区红色、超卖区绿色、中性蓝色 */
export const getRSIColor = (val: number): string => {
    if (val > 70) return "bg-rose-500";
    if (val < 30) return "bg-emerald-500";
    return "bg-blue-500";
};

// ========================================
// 引用高亮系统 (Reference Highlight System)
// ========================================

/** 滚动到指定元素并触发 3 秒高亮闪烁动画 */
export const highlightElement = (elementId: string) => {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.add('animate-highlight-flash');
        setTimeout(() => {
            element.classList.remove('animate-highlight-flash');
        }, 3000);
    }
};

/** 引用标签组件：点击后跳转至对应数据源卡片 */
export const ReferenceCitation = ({ id }: { id: string }) => {
    return (
        <button
            onClick={() => highlightElement(id)}
            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 mx-0.5 rounded-md bg-blue-500/10 hover:bg-blue-500/20 text-blue-500 text-[10px] font-black transition-colors border border-blue-500/20 group cursor-pointer"
            title="查看数据源"
        >
            <Link2 className="h-2.5 w-2.5" />
            <span>{id.replace('REF_', '')}</span>
        </button>
    );
};

// ========================================
// Markdown 渲染器 (带引用解析)
// ========================================

/**
 * 封装带 [[REF_X]] 引用解析的 Markdown 渲染器
 * 自动将文本中的 [[REF_T1]] 等标记替换为可点击的引用标签
 */
export const MarkdownWithRefs = ({ content }: { content: string }) => {
    /**
     * h3 计数器：通过闭包追踪当前 h3 的索引
     * 用于实现不同段落竖线颜色的轮换：
     *   第1段 → 蓝色 (操作建议/核心结论)
     *   第2段 → 绿色 (执行计划/可操作项)
     *   第3段+ → 灰色 (支撑逻辑/辅助信息)
     */
    let h3Counter = 0;
    const h3Colors = [
        'border-blue-500',      // 操作建议 — 最高优先级
        'border-emerald-500',   // 执行计划 — 可操作项
        'border-slate-400',     // 支撑逻辑 — 辅助信息
    ];

    return (
        <ReactMarkdown
            components={{
                h3: ({ node, ...props }) => {
                    const colorClass = h3Colors[Math.min(h3Counter, h3Colors.length - 1)];
                    const isFirst = h3Counter === 0;
                    h3Counter++;
                    return (
                        <h3
                            className={`text-sm font-bold text-slate-800 dark:text-white mb-2 flex items-center gap-2 border-l-4 ${colorClass} pl-3 tracking-wider ${isFirst ? 'mt-2' : 'mt-8'}`}
                            {...props}
                        />
                    );
                },
                strong: ({ node, ...props }) => (
                    <strong className="font-bold text-slate-900 dark:text-white px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-500/10" {...props} />
                ),
                ul: ({ node, ...props }) => (
                    <ul className="space-y-1 mt-2 list-none p-0" {...props} />
                ),
                li: ({ node, ...props }) => (
                    <li className="flex items-start gap-2 before:content-['•'] before:text-blue-500 before:font-black" {...props} />
                ),
                p: ({ node, ...props }) => {
                    const children = React.Children.toArray(props.children);
                    const processed = children.flatMap((child) => {
                        if (typeof child !== 'string') return child;

                        const parts = child.split(/(\[\[REF_[A-Z0-9]+\]\])/g);
                        return parts.map((part, i) => {
                            const match = part.match(/\[\[(REF_[A-Z0-9]+)\]\]/);
                            if (match) {
                                return <ReferenceCitation key={i} id={match[1]} />;
                            }
                            return part;
                        });
                    });
                    return <p className="mt-1.5 text-slate-500 dark:text-slate-400">{processed}</p>;
                }
            }}
        >
            {content}
        </ReactMarkdown>
    );
};
