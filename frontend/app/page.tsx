"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
// @ts-ignore
import { useAuth } from "@/context/AuthContext";
// @ts-ignore

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
// @ts-ignore
import { getPortfolio, analyzeStock, PortfolioItem, searchStocks, addPortfolioItem, SearchResult, deletePortfolioItem } from "@/lib/api";
import { RefreshCcw, Zap, Settings, Loader2, Trash2, Check, Pencil, Filter, X, Search } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from 'react-markdown';
import Link from 'next/link';

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Analysis State
  const [analyzing, setAnalyzing] = useState(false);
  const [aiData, setAiData] = useState<{ technical_analysis: string, fundamental_news: string, action_advice: string } | null>(null);

  // Search State
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [addingTicker, setAddingTicker] = useState<string | null>(null); // Loading state for API call

  // Edit & Filter State
  const [editingTicker, setEditingTicker] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ quantity: "", cost: "" });
  const [onlyHoldings, setOnlyHoldings] = useState(false);

  // Market Status State
  const [marketStatus, setMarketStatus] = useState<{
    status: 'open' | 'closed',
    text: string,
    countdown: string
  }>({ status: 'closed', text: 'Market Closed', countdown: '' });

  // Sorting State
  const [sortBy, setSortBy] = useState<"ticker" | "price" | "change">("ticker");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const sortedPortfolio = [...portfolio]
    .filter(item => !onlyHoldings || item.quantity > 0)
    .sort((a, b) => {
      let valA, valB;
      if (sortBy === "ticker") {
        valA = a.ticker;
        valB = b.ticker;
      } else if (sortBy === "price") {
        valA = a.current_price;
        valB = b.current_price;
      } else {
        valA = a.pl_percent;
        valB = b.pl_percent;
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

  const handleSort = (key: "ticker" | "price" | "change") => {
    if (sortBy === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(key);
      setSortOrder("asc");
    }
  };

  const { isAuthenticated } = useAuth();
  const router = useRouter();

  // Set mounted state and fetch initial data
  useEffect(() => {
    setMounted(true);
    fetchData();

    // Market Status Timer
    const calculateMarketStatus = () => {
      const now = new Date();
      // Get New York Time
      const nyTimeStr = now.toLocaleString("en-US", { timeZone: "America/New_York" });
      const nyDate = new Date(nyTimeStr);

      const day = nyDate.getDay(); // 0 = Sun, 6 = Sat
      const hours = nyDate.getHours();
      const minutes = nyDate.getMinutes();
      const timeInMinutes = hours * 60 + minutes;

      const openTime = 9 * 60 + 30; // 9:30 AM
      const closeTime = 16 * 60;    // 4:00 PM

      const isWeekend = day === 0 || day === 6;
      const isOpen = !isWeekend && timeInMinutes >= openTime && timeInMinutes < closeTime;

      let text = "";
      let countdown = "";
      let status: 'open' | 'closed' = isOpen ? 'open' : 'closed';

      if (isOpen) {
        text = "美股盘中 (OPEN)";
        const diff = closeTime - timeInMinutes;
        countdown = `距收盘: ${Math.floor(diff / 60)}h ${diff % 60}m`;
      } else {
        text = "美股休市 (CLOSED)";
        let diffMinutes = 0;

        if (isWeekend || timeInMinutes >= closeTime) {
          // Calculate minutes until next Monday 9:30 AM or next day 9:30 AM
          const daysToWait = day === 5 ? 3 : day === 6 ? 2 : day === 0 ? 1 : (timeInMinutes >= closeTime ? 1 : 0);
          const nextOpen = new Date(nyDate);
          nextOpen.setDate(nyDate.getDate() + daysToWait);
          nextOpen.setHours(9, 30, 0, 0);
          diffMinutes = Math.floor((nextOpen.getTime() - nyDate.getTime()) / 60000);
        } else {
          // Same day but before open
          diffMinutes = openTime - timeInMinutes;
        }

        const h = Math.floor(diffMinutes / 60);
        const m = diffMinutes % 60;
        countdown = `距开盘: ${h}h ${m}m`;
      }

      setMarketStatus({ status, text, countdown });
    };

    calculateMarketStatus();
    const interval = setInterval(calculateMarketStatus, 60000);
    return () => clearInterval(interval);
  }, []);

  // Redirect if not authenticated
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isAuthenticated && !localStorage.getItem("token")) {
        router.push("/login");
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, router]);


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

  const fetchData = async (refresh: boolean = false) => {
    if (!localStorage.getItem("token")) return;
    setLoading(true);
    try {
      const data = await getPortfolio(refresh);
      setPortfolio(data);
      // Auto-select first item if exists and nothing selected
      if (data.length > 0 && !selectedTicker) {
        setSelectedTicker(data[0].ticker);
      }
    } catch (error) {
      console.error("Failed to fetch portfolio", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchData(false); // ALWAYS instant from DB
  }, [isAuthenticated]);

  // Handle Selection
  useEffect(() => {
    // Reset AI data when switching stocks
    setAiData(null);
  }, [selectedTicker]);

  const handleAnalyze = async () => {
    if (!selectedTicker) return;
    setAnalyzing(true);
    try {
      const result = await analyzeStock(selectedTicker);
      // Parse JSON
      try {
        // AI Service now returns JSON string (hopefully)
        // We might need to sanitize markdown code blocks if the AI wraps it in ```json ... ```
        let raw = result.analysis;
        if (raw.startsWith("```json")) {
          raw = raw.replace("```json", "").replace("```", "");
        }
        const parsed = JSON.parse(raw);
        setAiData(parsed);
      } catch (parseErr) {
        console.warn("Failed to parse JSON", parseErr);
        // Fallback if AI returned plain text/markdown
        setAiData({
          technical_analysis: result.analysis,
          fundamental_news: "Could not parse structured data. Displaying raw output below.",
          action_advice: result.analysis
        });
      }
    } catch (error: any) {
      if (error.response?.status === 429) {
        alert("Limit Reached! 🛑\nPlease add your own API Key in Settings.");
        router.push("/settings");
      } else {
        alert("Analysis failed.");
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const selectedItem = portfolio.find(p => p.ticker === selectedTicker);

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-16 items-center px-4 border-b bg-white dark:bg-slate-900 shrink-0 gap-4">
        <h1 className="font-bold text-lg">AI Investment Advisor</h1>

        {/* Market Status Section */}
        <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-50 dark:bg-slate-800/50 rounded-full border border-slate-100 dark:border-slate-800">
          <div className={clsx(
            "h-2 w-2 rounded-full animate-pulse",
            marketStatus.status === 'open' ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500"
          )} />
          <div className="flex flex-col leading-none">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-tighter">{marketStatus.text}</span>
            <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">{marketStatus.countdown}</span>
          </div>
        </div>

        <div className="ml-auto flex gap-2">
          {/* Refresh removed to focus on background data logic */}
          <Link href="/settings">
            <Button variant="ghost" size="icon"><Settings className="h-4 w-4" /></Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={() => {
            localStorage.removeItem("token");
            router.push("/login");
          }}>
            Logout
          </Button>
        </div>
      </header>

      {/* Main Content (Master-Detail) */}
      <div className="flex-1 min-h-0 grid grid-cols-12 overflow-hidden">

        {/* Left: Stock List */}
        <div className="col-span-3 border-r bg-white dark:bg-slate-900 flex flex-col h-full overflow-hidden">
          <div className="p-4 border-b font-medium text-sm text-slate-500 flex justify-between items-center bg-slate-50/50">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-700 dark:text-slate-300">股票列表</span>
              <Button
                variant={onlyHoldings ? "secondary" : "ghost"}
                size="icon"
                className="h-6 w-6"
                title="只看持仓"
                onClick={() => setOnlyHoldings(!onlyHoldings)}
              >
                <Filter className={clsx("h-3 w-3", onlyHoldings && "text-blue-500")} />
              </Button>
            </div>
            <Button variant="outline" size="icon" className="h-6 w-6" onClick={() => {
              setIsSearchOpen(true);
              setSearching(true);
              searchStocks("")
                .then(res => setSearchResults(res))
                .catch(err => console.error("Search failed", err))
                .finally(() => setSearching(false));
            }}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* Table Headers */}
          <div className="grid grid-cols-3 px-4 py-2 border-b text-[10px] uppercase tracking-wider font-bold text-slate-400 bg-slate-50/50 dark:bg-slate-800/20">
            <div className="cursor-pointer hover:text-blue-500 transition-colors flex items-center gap-1" onClick={() => handleSort("ticker")}>
              代码 {sortBy === "ticker" && (sortOrder === "asc" ? "↑" : "↓")}
            </div>
            <div className="cursor-pointer hover:text-blue-500 transition-colors flex items-center justify-center gap-1" onClick={() => handleSort("price")}>
              价格 {sortBy === "price" && (sortOrder === "asc" ? "↑" : "↓")}
            </div>
            <div className="cursor-pointer hover:text-blue-500 transition-colors flex items-center justify-end gap-1" onClick={() => handleSort("change")}>
              涨幅 {sortBy === "change" && (sortOrder === "asc" ? "↑" : "↓")}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {sortedPortfolio.map(item => (
              <div
                key={item.ticker}
                className={clsx(
                  "border-b transition-all duration-200",
                  selectedTicker === item.ticker ? "bg-blue-50/50 dark:bg-blue-900/10 border-l-4 border-l-blue-500" : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                )}
              >
                {/* ALWAYS show the Display Section */}
                <div
                  onClick={() => setSelectedTicker(item.ticker)}
                  className="p-4 cursor-pointer relative group"
                >
                  <div className="grid grid-cols-3 items-center mb-1">
                    <span className="font-bold text-sm text-slate-700 dark:text-slate-300">{item.ticker}</span>
                    <span className="text-center font-mono text-xs text-slate-600 dark:text-slate-400">${item.current_price.toFixed(2)}</span>
                    <span className={clsx(
                      "text-right text-xs font-bold",
                      (item.change_percent || 0) >= 0 ? "text-green-600" : "text-red-500"
                    )}>
                      {(item.change_percent || 0) >= 0 ? "+" : ""}{(item.change_percent || 0).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-end mt-1">
                    <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2">
                      {item.quantity > 0 ? (
                        <>
                          <span className="bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 px-1 rounded font-bold border border-green-100 dark:border-green-800">HOLD {item.quantity}</span>
                          <span className="text-slate-300 dark:text-slate-600">|</span>
                          <span>AVG: {item.avg_cost.toFixed(2)}</span>
                        </>
                      ) : (
                        <span className="text-slate-300 italic">WATCHING</span>
                      )}
                      {item.last_updated && (
                        <>
                          <span className="text-slate-300 dark:text-slate-600">|</span>
                          <span className="text-[9px] opacity-60">
                            更新于 {mounted ? formatDistanceToNow(new Date(item.last_updated + 'Z'), { addSuffix: true, locale: zhCN }) : "..."}
                          </span>
                        </>
                      )}
                    </div>
                    <div className={clsx(
                      "flex gap-1 transition-opacity",
                      editingTicker === item.ticker ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                    )}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={clsx("h-7 w-7", editingTicker === item.ticker ? "text-blue-500 bg-blue-50" : "text-slate-300 hover:text-blue-500 hover:bg-blue-50")}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (editingTicker === item.ticker) {
                            setEditingTicker(null);
                          } else {
                            setEditingTicker(item.ticker);
                            setEditForm({ quantity: item.quantity.toString(), cost: item.avg_cost.toString() });
                          }
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-slate-300 hover:text-red-500 hover:bg-red-50"
                        onClick={async (e) => {
                          e.stopPropagation();
                          await deletePortfolioItem(item.ticker);
                          await fetchData();
                          if (selectedTicker === item.ticker) setSelectedTicker(null);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* EXPANDABLE Edit Section - Compact Single Row */}
                {editingTicker === item.ticker && (
                  <div className="px-4 pb-4 animate-in slide-in-from-top-1 duration-200" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                      <div className="flex items-center gap-1.5 flex-1">
                        <div className="relative flex-1">
                          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-bold">持</span>
                          <Input
                            type="number"
                            className="h-7 text-[11px] pl-6 pr-1 bg-white dark:bg-slate-900 border-slate-200 focus:border-blue-400 transition-colors shadow-none"
                            value={editForm.quantity}
                            onChange={e => setEditForm({ ...editForm, quantity: e.target.value })}
                          />
                        </div>
                        <div className="relative flex-1">
                          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 font-bold">均</span>
                          <Input
                            type="number"
                            className="h-7 text-[11px] pl-6 pr-1 bg-white dark:bg-slate-900 border-slate-200 focus:border-blue-400 transition-colors shadow-none"
                            value={editForm.cost}
                            onChange={e => setEditForm({ ...editForm, cost: e.target.value })}
                          />
                        </div>
                      </div>
                      <Button
                        size="sm"
                        className="h-7 px-3 bg-blue-600 hover:bg-blue-700 text-[11px] font-bold"
                        onClick={async () => {
                          try {
                            await addPortfolioItem(
                              item.ticker,
                              parseFloat(editForm.quantity) || 0,
                              parseFloat(editForm.cost) || 0
                            );
                            await fetchData();
                            setEditingTicker(null);
                          } catch (err) {
                            alert("更新失败");
                          }
                        }}
                      >
                        确定
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-slate-300 hover:text-slate-500"
                        onClick={() => setEditingTicker(null)}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {
              sortedPortfolio.length === 0 && !loading && (
                <div className="p-12 text-center text-slate-400 text-sm italic">
                  列表为空
                </div>
              )
            }
          </div>
        </div>

        {/* Right: Detail View */}
        <div className="col-span-9 bg-slate-50 dark:bg-slate-950 p-6 flex flex-col gap-6 overflow-y-auto h-full custom-scrollbar">
          {!selectedItem ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-300 gap-2">
              <Zap className="h-12 w-12 opacity-10" />
              <p className="text-sm font-medium">请从左侧选择一个代码查看详情</p>
            </div>
          ) : (
            <>
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-4xl font-black tracking-tight text-slate-800 dark:text-slate-100">{selectedItem.ticker}</h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <p className="text-lg font-mono text-slate-500">Price: <span className="text-slate-800 dark:text-slate-200 font-bold">${selectedItem.current_price.toFixed(2)}</span></p>
                    <span className="text-slate-300">|</span>
                    <p className="text-lg font-mono text-slate-500">Value: <span className="text-blue-600 font-bold">${selectedItem.market_value.toFixed(2)}</span></p>
                    <span className="text-slate-300">|</span>
                    <p className="text-sm font-mono text-slate-500">Size: <span className="text-slate-800 dark:text-slate-200 font-bold">{selectedItem.quantity}</span></p>
                    <span className="text-slate-300">|</span>
                    <p className="text-sm font-mono text-slate-500">Avg Cost: <span className="text-slate-800 dark:text-slate-200 font-bold">${selectedItem.avg_cost.toFixed(2)}</span></p>
                  </div>
                </div>
                <Button onClick={handleAnalyze} disabled={analyzing} size="lg" className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 px-8 py-6 text-lg font-bold">
                  <Zap className={clsx("mr-2 h-5 w-5", analyzing && "animate-pulse")} />
                  {analyzing ? "AI 正在分析深度数据..." : "AI 深度分析"}
                </Button>
              </div>

              {/* AI Analysis Cards */}
              <div className="grid gap-6">
                {/* 1. Fundamentals */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800">
                  <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20">
                    <CardTitle className="text-sm font-bold flex items-center gap-2 uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      基本面数据 (Fundamentals)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    {/* Fundamental Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                      {[
                        { label: "Market Cap", value: selectedItem.market_cap ? (selectedItem.market_cap / 1e9).toFixed(1) + "B" : "-" },
                        { label: "PE Ratio", value: selectedItem.pe_ratio?.toFixed(2) || "-" },
                        { label: "Forward PE", value: selectedItem.forward_pe?.toFixed(2) || "-" },
                        { label: "EPS", value: selectedItem.eps?.toFixed(2) || "-" },
                        { label: "Beta", value: selectedItem.beta?.toFixed(2) || "-" },
                        { label: "Div Yield", value: selectedItem.dividend_yield ? (selectedItem.dividend_yield * 100).toFixed(2) + "%" : "-" },
                        { label: "52W High", value: selectedItem.fifty_two_week_high?.toFixed(2) || "-" },
                        { label: "52W Low", value: selectedItem.fifty_two_week_low?.toFixed(2) || "-" },
                        { label: "Sector", value: selectedItem.sector || "-" },
                        { label: "Industry", value: selectedItem.industry || "-" },
                      ].map(stat => (
                        <div key={stat.label} className="flex flex-col p-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded shadow-sm">
                          <span className="text-[9px] text-slate-400 font-bold uppercase truncate">{stat.label}</span>
                          <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 truncate">{stat.value}</span>
                        </div>
                      ))}
                    </div>

                    {aiData && (
                      <div className="prose dark:prose-invert text-sm max-w-none leading-relaxed border-t pt-4">
                        <ReactMarkdown>{aiData.fundamental_news}</ReactMarkdown>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* 2. Technical Indicators */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800 overflow-hidden">
                  <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2 uppercase tracking-wider text-slate-600 dark:text-slate-400">
                      技术指标 (Technical Indicators)
                    </CardTitle>
                    {selectedItem.last_updated && (
                      <div className="text-[10px] text-slate-400 font-mono">
                        数据时间: {formatDistanceToNow(new Date(selectedItem.last_updated + 'Z'), { addSuffix: true, locale: zhCN })}
                      </div>
                    )}
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    {/* Technical Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                      {[
                        { label: "RSI (14)", value: selectedItem.rsi_14?.toFixed(2) || "-" },
                        { label: "MA 20", value: selectedItem.ma_20?.toFixed(2) || "-" },
                        { label: "MA 50", value: selectedItem.ma_50?.toFixed(2) || "-" },
                        { label: "MA 200", value: selectedItem.ma_200?.toFixed(2) || "-" },
                        { label: "MACD", value: selectedItem.macd_val?.toFixed(2) || "-" },
                        { label: "MACD Hist", value: selectedItem.macd_hist?.toFixed(2) || "-" },
                        { label: "ATR (14)", value: selectedItem.atr_14?.toFixed(2) || "-" },
                        { label: "BB Upper", value: selectedItem.bb_upper?.toFixed(2) || "-" },
                        { label: "BB Lower", value: selectedItem.bb_lower?.toFixed(2) || "-" },
                        { label: "KDJ - K", value: selectedItem.k_line?.toFixed(1) || "-" },
                        { label: "KDJ - D", value: selectedItem.d_line?.toFixed(1) || "-" },
                        { label: "Vol Ratio", value: selectedItem.volume_ratio?.toFixed(2) || "-" },
                      ].map(stat => (
                        <div key={stat.label} className="flex flex-col p-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded shadow-sm">
                          <span className="text-[9px] text-slate-400 font-bold uppercase truncate">{stat.label}</span>
                          <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 truncate">{stat.value}</span>
                        </div>
                      ))}
                    </div>

                    {aiData && (
                      <div className="prose dark:prose-invert text-sm max-w-none leading-relaxed border-t pt-4">
                        <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* 3. AI Advice */}
                <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-900/5 shadow-md shadow-blue-500/5">
                  <CardHeader className="pb-2 border-b border-blue-100 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-900/20"><CardTitle className="text-base font-bold text-blue-700 dark:text-blue-400 flex items-center gap-2">AI 给出的操作建议 (Actionable Advice)</CardTitle></CardHeader>
                  <CardContent className="pt-4 pb-6">
                    {aiData ? (
                      <div className="prose dark:prose-invert text-base max-w-none font-medium text-blue-900 dark:text-blue-100 leading-relaxed bg-white/50 dark:bg-slate-900/50 p-4 rounded-lg border border-blue-50 dark:border-blue-900/30">
                        <ReactMarkdown>{aiData.action_advice}</ReactMarkdown>
                      </div>
                    ) : <div className="text-blue-300/50 italic text-sm py-4 italic">等待分析中...</div>}
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Search Dialog */}
      <Dialog open={isSearchOpen} onOpenChange={setIsSearchOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>添加自选股</DialogTitle>
            <DialogDescription>搜索股票代码并添加到您的投资组合。</DialogDescription>
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
                        // Local search only on type
                        const res = await searchStocks(val.trim(), false);
                        setSearchResults(res);
                      } catch (err) { console.error(err) }
                      finally { setSearching(false); }
                    } else {
                      setSearchResults([]);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRemoteSearch();
                  }}
                />
                {searching && <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-slate-400" />}
              </div>
              <Button onClick={handleRemoteSearch} disabled={searching} className="bg-blue-600 hover:bg-blue-700">
                <Search className="h-4 w-4" />
              </Button>
            </div>

            <ScrollArea className="h-[300px] border rounded-md p-2">
              {searchResults.length === 0 && !searching && (
                <div className="text-center text-sm text-slate-400 p-8 italic">未找到相关股票</div>
              )}
              {searchResults.map(stock => (
                <div key={stock.ticker} className="flex flex-col border-b last:border-0">
                  <div
                    className="flex justify-between items-center p-3 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors group cursor-default"
                  >
                    <div>
                      <div className="font-bold text-sm text-slate-700 dark:text-slate-300">{stock.ticker}</div>
                      <div className="text-[11px] text-slate-500">{stock.name}</div>
                    </div>
                    <Button
                      size="sm"
                      variant={portfolio.some(p => p.ticker === stock.ticker) ? "secondary" : "default"}
                      className="h-8"
                      disabled={addingTicker === stock.ticker || portfolio.some(p => p.ticker === stock.ticker)}
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (portfolio.some(p => p.ticker === stock.ticker)) return;

                        setAddingTicker(stock.ticker);
                        try {
                          await addPortfolioItem(stock.ticker, 0, 0);
                          await fetchData();
                        } catch (err) {
                          console.error(err);
                          alert("添加失败");
                        } finally {
                          setAddingTicker(null);
                        }
                      }}
                    >
                      {addingTicker === stock.ticker ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : portfolio.some(p => p.ticker === stock.ticker) ? (
                        <span className="flex items-center text-green-600 font-bold"><Check className="h-4 w-4 mr-1" /> 已添加</span>
                      ) : (
                        "添加"
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </ScrollArea>
          </div>
        </DialogContent >
      </Dialog >
    </div>

  );
}
