/**
 * 实时资讯流板块 (News Feed Section)
 * 职责：展示个股相关的实时新闻列表
 * 布局规范：标题顶格、内容缩进
 */
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Activity } from "lucide-react";
import { StockNewsList } from "../StockNewsList";
import { NewsFeedProps, AIData } from "./types";
import { ReferenceCitation } from "./shared";

export const NewsFeed = React.memo(function NewsFeed({ news, aiData }: NewsFeedProps & { aiData?: AIData | null }) {
    return (
        <div className="space-y-8 pt-4">
            {/* 标题栏：顶格对齐（修正：移除原有的 px-4 md:px-10） */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-1.5 bg-slate-900 dark:bg-slate-100 rounded-full shadow-[0_0_12px_rgba(15,23,42,0.3)] dark:shadow-[0_0_12px_rgba(241,245,249,0.3)]" />
                    <h2 className="text-xl font-black tracking-tight text-slate-900 dark:text-slate-100 uppercase">实时资讯流 (News)</h2>
                </div>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full mr-4 md:mr-10">
                    {news.length} Articles
                </span>
            </div>

            {/* 消息面综述卡片 */}
            {aiData?.fundamental_news && (
                <div className="px-4 md:px-10">
                    <div className="mt-4 bg-slate-50/80 dark:bg-zinc-800/20 border border-slate-200/50 dark:border-zinc-800/50 rounded-2xl p-4 md:p-5 flex flex-col md:flex-row gap-4 items-start">
                        {/* 侧边标题 */}
                        <div className="flex items-center gap-2 shrink-0 md:w-28 md:pt-1">
                            <div className="h-3 w-1 bg-slate-900 dark:bg-white rounded-full shrink-0" />
                            <h3 className="text-[10px] font-black uppercase text-slate-500 dark:text-zinc-400 tracking-[0.2em] whitespace-nowrap">消息面综述</h3>
                        </div>

                        <div className="flex-1 min-w-0 md:border-l border-slate-200/50 dark:border-zinc-800/50 md:pl-5">
                            <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                                <div className="text-[12px] leading-snug text-slate-600 dark:text-zinc-400">
                                    <ReactMarkdown
                                        components={{
                                            h3: ({ node, ...props }) => (
                                                <h3 className="font-bold text-blue-600 dark:text-blue-400 mt-4 mb-2 first:mt-0 text-sm block">
                                                    {props.children}
                                                </h3>
                                            ),
                                            h4: ({ node, ...props }) => (
                                                <h4 className="font-bold text-blue-600 dark:text-blue-400 mt-3 mb-1 first:mt-0 text-sm block">
                                                    {props.children}
                                                </h4>
                                            ),
                                            strong: ({ node, ...props }) => (
                                                <strong className="font-bold text-blue-600 dark:text-blue-400">
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
                                                return <p className="mt-0 mb-2 last:mb-0 block w-full">{processed}</p>;
                                            }
                                        }}
                                    >
                                        {(aiData.fundamental_news || '').replace(/([。！？；;：:\.!\?])\s+(\*\*.*?\*\*\s*[:：])/g, '$1\n\n$2')}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 内容区：缩进 */}
            <div className="px-4 md:px-10">
                <StockNewsList news={news} />
            </div>
        </div>
    );
});
