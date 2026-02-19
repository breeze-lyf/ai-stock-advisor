"use client";

import React from "react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import { ExternalLink, Clock, Newspaper, Zap } from "lucide-react";
import ReactMarkdown from "react-markdown";
import clsx from "clsx";

interface NewsItem {
    id: string;
    title: string;
    publisher: string;
    link: string;
    publish_time: string;
    summary?: string;
}

interface StockNewsListProps {
    news: NewsItem[];
}

export function StockNewsList({ news }: StockNewsListProps) {
    if (!news || news.length === 0) {
        return (
            <div className="py-12 flex flex-col items-center justify-center text-slate-400 bg-slate-50/50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
                <Newspaper className="h-10 w-10 mb-3 opacity-20" />
                <p className="text-sm font-medium">暂无相关新闻动态</p>
            </div>
        );
    }

    // Deduplicate news based on title or link to handle existing duplicates
    const uniqueNews = Array.from(new Map(news.map(item => [item.link || item.title, item])).values());

    return (
        <div className="space-y-6">
            {uniqueNews.map((item) => {
                const isTavily = item.id?.startsWith('tavily-');
                
                return (
                    <div
                        key={item.id}
                        className={clsx(
                            "group relative pl-6 border-l-2 transition-all duration-300",
                            isTavily 
                                ? "border-blue-500 bg-blue-500/5 py-4 -ml-2 pl-[calc(1.5rem-8px)] rounded-r-2xl" 
                                : "border-slate-100 dark:border-slate-800 hover:border-blue-500"
                        )}
                    >
                        <div className={clsx(
                            "absolute -left-[5px] top-1 h-2 w-2 rounded-full transition-colors",
                            isTavily ? "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" : "bg-slate-200 dark:bg-slate-700 group-hover:bg-blue-500"
                        )} />

                        <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest">
                                {isTavily && (
                                    <span className="bg-blue-600 text-white px-1.5 py-0.5 rounded flex items-center gap-1 scale-90 -ml-1">
                                        <Zap className="h-2 w-2 fill-current" /> AI INSIGHT
                                    </span>
                                )}
                                <span className="flex items-center gap-1 text-slate-400">
                                    <Clock className="h-3 w-3" />
                                    {formatDistanceToNow(new Date(item.publish_time + (item.publish_time.includes('Z') ? '' : 'Z')), { addSuffix: true, locale: zhCN })}
                                </span>
                                <span className="h-1 w-1 rounded-full bg-slate-300" />
                                <span className="text-slate-500 dark:text-slate-400">{item.publisher}</span>
                            </div>

                            <a
                                href={item.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-lg font-black text-slate-800 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors leading-tight flex items-start gap-2"
                            >
                                {item.title}
                                <ExternalLink className="h-4 w-4 mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </a>

                            {item.summary && (
                                <div className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium line-clamp-3">
                                    <ReactMarkdown>{item.summary}</ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
