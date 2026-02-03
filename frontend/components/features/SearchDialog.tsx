"use client";

import React, { useState } from "react";
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
import { searchStocks, addPortfolioItem } from "@/lib/api";

interface SearchDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    onRefresh: () => void;
    portfolio: PortfolioItem[];
}

export function SearchDialog({
    isOpen,
    onOpenChange,
    onRefresh,
    portfolio,
}: SearchDialogProps) {
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [addingTicker, setAddingTicker] = useState<string | null>(null);

    const handleRemoteSearch = async () => {
        if (!searchQuery.trim()) return;
        setSearching(true);
        try {
            const res = await searchStocks(searchQuery.trim(), true);
            setSearchResults(res);
        } catch (err) {
            console.error("Remote search failed", err);
        } finally {
            setSearching(false);
        }
    };

    const handleAddTicker = async (ticker: string) => {
        if (portfolio.some((p) => p.ticker === ticker)) return;

        setAddingTicker(ticker);
        try {
            await addPortfolioItem(ticker, 0, 0);
            onRefresh();
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
                                    if (val.trim()) {
                                        setSearching(true);
                                        try {
                                            const res = await searchStocks(val.trim(), false);
                                            setSearchResults(res);
                                        } catch (err) {
                                            console.error(err);
                                        } finally {
                                            setSearching(false);
                                        }
                                    } else {
                                        setSearchResults([]);
                                    }
                                }}
                                onKeyDown={handleSearchKeyPress}
                            />
                            {searching && (
                                <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-slate-400" />
                            )}
                        </div>
                        <Button
                            onClick={handleRemoteSearch}
                            disabled={searching}
                            className="bg-blue-600 hover:bg-blue-700"
                        >
                            <Search className="h-4 w-4" />
                        </Button>
                    </div>

                    <ScrollArea className="h-[300px] border rounded-md p-2">
                        {searchResults.length === 0 && !searching && (
                            <div className="text-center text-sm text-slate-400 p-8 italic">
                                未找到相关股票
                            </div>
                        )}
                        {searchResults.map((stock) => (
                            <div
                                key={stock.ticker}
                                className="flex flex-col border-b last:border-0"
                            >
                                <div className="flex justify-between items-center p-3 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors group cursor-default">
                                    <div>
                                        <div className="font-bold text-sm text-slate-700 dark:text-slate-300">
                                            {stock.ticker}
                                        </div>
                                        <div className="text-[11px] text-slate-500">{stock.name}</div>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant={
                                            portfolio.some((p) => p.ticker === stock.ticker)
                                                ? "secondary"
                                                : "default"
                                        }
                                        className="h-8"
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
