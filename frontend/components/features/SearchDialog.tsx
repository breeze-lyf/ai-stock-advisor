"use client";

import React, { useEffect, useRef, useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Loader2, Check } from "lucide-react";
import { PortfolioItem, SearchResult } from "@/types";
import { addPortfolioItem, searchStocks } from "@/features/portfolio/api";

interface SearchDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    onRefresh: () => void;
    onSelectTicker?: (ticker: string) => void;
    portfolio: PortfolioItem[];
}

export function SearchDialog({
    isOpen,
    onOpenChange,
    onRefresh,
    onSelectTicker,
    portfolio,
}: SearchDialogProps) {
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [addingTicker, setAddingTicker] = useState<string | null>(null);
    const [hasSearched, setHasSearched] = useState(false);
    const [searchHint, setSearchHint] = useState("输入时先检索本地已缓存标的，点击右侧搜索或按回车会触发全市场远程检索。");
    const localRequestIdRef = useRef(0);
    const remoteRequestIdRef = useRef(0);
    const remoteAbortRef = useRef<AbortController | null>(null);
    const localDebounceRef = useRef<number | null>(null);

    useEffect(() => {
        if (!isOpen) {
            remoteAbortRef.current?.abort();
            remoteAbortRef.current = null;
            if (localDebounceRef.current) {
                window.clearTimeout(localDebounceRef.current);
                localDebounceRef.current = null;
            }
            setSearching(false);
        }
    }, [isOpen]);

    useEffect(() => {
        return () => {
            remoteAbortRef.current?.abort();
            if (localDebounceRef.current) {
                window.clearTimeout(localDebounceRef.current);
            }
        };
    }, []);

    const clearSearch = () => {
        remoteAbortRef.current?.abort();
        remoteAbortRef.current = null;
        if (localDebounceRef.current) {
            window.clearTimeout(localDebounceRef.current);
            localDebounceRef.current = null;
        }
        setSearchResults([]);
        setHasSearched(false);
        setSearching(false);
        setSearchHint("输入时先检索本地已缓存标的，点击右侧搜索或按回车会触发全市场远程检索。");
    };

    const runLocalSearch = async (rawQuery: string) => {
        const query = rawQuery.trim();
        if (!query) {
            clearSearch();
            return;
        }

        if (query.length < 2) {
            setSearchResults([]);
            setHasSearched(false);
            setSearchHint("至少输入 2 个字符后再开始本地检索。");
            return;
        }

        const requestId = ++localRequestIdRef.current;
        setHasSearched(true);
        setSearchHint("正在检索本地已缓存标的...");

        try {
            const res = await searchStocks(query, false);
            if (requestId !== localRequestIdRef.current) {
                return;
            }
            setSearchResults(res);
            setSearchHint(
                res.length > 0
                    ? `已找到 ${res.length} 个结果`
                    : "本地未命中，可点击右侧搜索触发远程检索。"
            );
        } catch (err) {
            if (requestId !== localRequestIdRef.current) {
                return;
            }
            console.error("Local search failed", err);
            setSearchResults([]);
            setSearchHint("本地搜索失败，请稍后重试。");
        }
    };

    const runRemoteSearch = async (rawQuery: string) => {
        const query = rawQuery.trim();
        if (!query) {
            clearSearch();
            return;
        }

        const requestId = ++remoteRequestIdRef.current;
        remoteAbortRef.current?.abort();

        const controller = new AbortController();
        remoteAbortRef.current = controller;
        const timeout = window.setTimeout(() => controller.abort(), 4000);

        setSearching(true);
        setHasSearched(true);
        setSearchHint("正在执行全市场远程检索...");

        try {
            const res = await searchStocks(query, true, { signal: controller.signal });
            if (requestId !== remoteRequestIdRef.current) {
                return;
            }
            setSearchResults(res);
            setSearchHint(res.length > 0 ? `已找到 ${res.length} 个结果` : "未找到相关标的，已停止远程搜索。");
        } catch (err) {
            if (requestId !== remoteRequestIdRef.current) {
                return;
            }
            const isAbort = err instanceof Error && (err.name === "CanceledError" || err.name === "AbortError");
            if (isAbort) {
                setSearchHint(
                    searchResults.length > 0
                        ? "远程搜索超时，已保留当前结果。"
                        : "远程搜索超时，已停止本次搜索。"
                );
            } else {
                console.error("Remote search failed", err);
                setSearchHint(
                    searchResults.length > 0
                        ? "远程搜索失败，已保留当前结果。"
                        : "远程搜索失败，已停止本次搜索。"
                );
            }
        } finally {
            window.clearTimeout(timeout);
            if (requestId === remoteRequestIdRef.current) {
                setSearching(false);
            }
        }
    };

    const handleRemoteSearch = async () => {
        await runRemoteSearch(searchQuery);
    };

    const handleAddTicker = async (ticker: string) => {
        if (portfolio.some((p) => p.ticker === ticker)) return;

        setAddingTicker(ticker);
        try {
            await addPortfolioItem(ticker, 0, 0);
            
            // 后端 addPortfolioItem 已经触发了 background_fetch，
            // 这里我们不需要阻塞式等待深度刷新，直接关闭弹窗并刷新列表即可。
            
            // 立即关闭弹窗
            onOpenChange(false);
            
            // 异步刷新列表
            void onRefresh();
            
            // 自动跳转
            if (onSelectTicker) {
                onSelectTicker(ticker);
            }
        } catch (err) {
            console.error(err);
            alert("添加失败");
        } finally {
            setAddingTicker(null);
        }
    };

    const handleSearchKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            handleRemoteSearch();
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>添加自选股</DialogTitle>
                    <DialogDescription>
                        搜索股票代码并添加到您的投资组合。
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Input
                                placeholder="输入代码并点击搜索 (如 AAPL)..."
                                value={searchQuery}
                                onChange={async (e) => {
                                    const val = e.target.value;
                                    setSearchQuery(val);
                                    if (localDebounceRef.current) {
                                        window.clearTimeout(localDebounceRef.current);
                                    }

                                    if (!val.trim()) {
                                        clearSearch();
                                        return;
                                    }

                                    localDebounceRef.current = window.setTimeout(() => {
                                        void runLocalSearch(val);
                                    }, 250);
                                }}
                                onKeyDown={handleSearchKeyPress}
                                className="h-12 rounded-2xl border-slate-200 bg-white pr-11 text-base shadow-sm transition focus-visible:ring-2 focus-visible:ring-blue-500/30 dark:border-slate-700 dark:bg-slate-950"
                            />
                            {searching && (
                                <Loader2 className="absolute right-4 top-4 h-4 w-4 animate-spin text-slate-400" />
                            )}
                        </div>
                        <Button
                            onClick={handleRemoteSearch}
                            disabled={searching}
                            className="h-12 rounded-2xl bg-blue-600 px-4 hover:bg-blue-700"
                        >
                            <Search className="h-4 w-4" />
                        </Button>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            支持代码
                        </span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">AAPL / ASTS</span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">700 / 00700.HK</span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">510300</span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 dark:bg-slate-800">Apple / 腾讯 / 沪深300ETF</span>
                    </div>

                    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-400">
                        {searchHint}
                    </div>

                    <ScrollArea className="h-[320px] rounded-2xl border border-slate-200 bg-white p-2 shadow-inner dark:border-slate-800 dark:bg-slate-950">
                        {searchResults.length === 0 && !searching && !hasSearched && (
                            <div className="flex h-full min-h-[260px] flex-col items-center justify-center text-center">
                                <div className="mb-3 rounded-2xl bg-blue-50 p-3 text-blue-600 dark:bg-blue-950/40 dark:text-blue-300">
                                    <Search className="h-5 w-5" />
                                </div>
                                <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">开始搜索标的</div>
                                <div className="mt-2 max-w-[280px] text-xs leading-6 text-slate-500 dark:text-slate-400">
                                    你可以按代码或名称查找美股、港股、A 股和国内基金，再一键加入自选。
                                </div>
                            </div>
                        )}

                        {searchResults.length === 0 && !searching && hasSearched && (
                            <div className="flex h-full min-h-[260px] flex-col items-center justify-center text-center">
                                <div className="mb-3 rounded-2xl bg-slate-100 p-3 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                                    <Search className="h-5 w-5" />
                                </div>
                                <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">未找到相关标的</div>
                                <div className="mt-2 max-w-[280px] text-xs leading-6 text-slate-500 dark:text-slate-400">
                                    试试更完整的代码格式，或点击搜索按钮触发远程检索。
                                </div>
                            </div>
                        )}
                        {searchResults.map((stock) => (
                            <div
                                key={stock.ticker}
                                className="flex flex-col"
                            >
                                <div className="group mb-2 flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50/70 p-3 transition-colors hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:bg-slate-800">
                                    <div>
                                        <div className="text-sm font-black tracking-wide text-slate-800 dark:text-slate-100">
                                            {stock.ticker}
                                        </div>
                                        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{stock.name}</div>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant={
                                            portfolio.some((p) => p.ticker === stock.ticker)
                                                ? "secondary"
                                                : "default"
                                        }
                                        className="h-9 rounded-xl px-4"
                                        disabled={
                                            addingTicker === stock.ticker ||
                                            portfolio.some((p) => p.ticker === stock.ticker)
                                        }
                                        onClick={() => handleAddTicker(stock.ticker)}
                                    >
                                        {addingTicker === stock.ticker ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : portfolio.some((p) => p.ticker === stock.ticker) ? (
                                            <span className="flex items-center text-green-600 font-bold">
                                                <Check className="h-4 w-4 mr-1" /> 已添加
                                            </span>
                                        ) : (
                                            "添加"
                                        )}
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </ScrollArea>
                </div>
            </DialogContent>
        </Dialog>
    );
}
