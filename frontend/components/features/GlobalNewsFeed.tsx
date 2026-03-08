"use client";

import { useState, useEffect } from "react";
import { getClsNews } from "@/lib/api";
import { GlobalNews } from "@/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, RefreshCw, MessageSquare } from "lucide-react";
import clsx from "clsx";

export function GlobalNewsFeed() {
    const [news, setNews] = useState<GlobalNews[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchNews = async (refresh = false) => {
        setLoading(true);
        try {
            const data = await getClsNews(refresh);
            setNews(data);
        } catch (error) {
            console.error("Failed to fetch CLS news:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNews(false);
        // 每 2 分钟自动刷新一次
        const interval = setInterval(() => fetchNews(false), 120000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 uppercase tracking-tight">
                        财联社全球资讯 <span className="text-[10px] font-normal text-slate-400 ml-1">7x24H</span>
                    </h3>
                </div>
                <button 
                    onClick={() => fetchNews(true)} 
                    disabled={loading}
                    title="刷新快讯"
                    aria-label="刷新快讯"
                    className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={clsx("w-3.5 h-3.5 text-slate-500", loading && "animate-spin")} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-4 space-y-6 relative">
                    {/* Vertical Line */}
                    <div className="absolute left-[21px] top-6 bottom-6 w-0.5 bg-slate-100 dark:bg-slate-800" />

                    {news.length === 0 && !loading ? (
                        <div className="text-center py-10">
                            <p className="text-xs text-slate-400">暂无滚动快讯</p>
                        </div>
                    ) : (
                        news.map((item, idx) => {
                            // 格式化时间，只保留时分
                            const displayTime = item.time.includes(" ") ? item.time.split(" ")[1].substring(0, 5) : item.time;
                            
                            return (
                                <div key={idx} className="relative pl-6 group">
                                    {/* Timeline Dot */}
                                    <div className="absolute left-[3px] top-1.5 w-2 h-2 rounded-full bg-blue-600 ring-4 ring-white dark:ring-slate-900 z-10" />
                                    
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-bold font-mono text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0.5 rounded">
                                                {displayTime}
                                            </span>
                                            {item.title && (
                                                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-snug">
                                                    {item.title}
                                                </h4>
                                            )}
                                        </div>
                                        <div className="text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-wrap">
                                            {item.content}
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
            
            <div className="p-3 bg-slate-50 dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800 flex items-center justify-center">
                <p className="text-[9px] text-slate-400 uppercase tracking-widest flex items-center gap-1">
                    <MessageSquare className="w-2.5 h-2.5" /> Source: Cailianshe Terminal
                </p>
            </div>
        </div>
    );
}
