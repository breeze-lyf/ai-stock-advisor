"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { RefreshCcw, Zap, Settings, Loader2, Trash2, Check, Pencil, Filter, X } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from 'react-markdown';
import Link from 'next/link';

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);
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

  // Redirect if not authenticated
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isAuthenticated && !localStorage.getItem("token")) {
        router.push("/login");
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, router]);

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
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      {/* Header */}
      <header className="flex h-14 items-center px-4 border-b bg-white dark:bg-slate-900 shrink-0">
        <h1 className="font-bold text-lg mr-auto">AI Investment Advisor</h1>
        <div className="flex gap-2">
          <Button onClick={() => fetchData(true)} variant="ghost" size="icon" disabled={loading}>
            <RefreshCcw className={clsx("h-4 w-4", loading && "animate-spin")} />
          </Button>
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
      <div className="flex-1 overflow-hidden grid grid-cols-12">

        {/* Left: Stock List */}
        <div className="col-span-3 border-r bg-white dark:bg-slate-900 flex flex-col">
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

          <ScrollArea className="flex-1">
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
                      item.pl_percent >= 0 ? "text-green-600" : "text-red-500"
                    )}>
                      {item.pl_percent >= 0 ? "+" : ""}{item.pl_percent.toFixed(2)}%
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
                          if (confirm(`Delete ${item.ticker}?`)) {
                            await deletePortfolioItem(item.ticker);
                            await fetchData();
                            if (selectedTicker === item.ticker) setSelectedTicker(null);
                          }
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
            {sortedPortfolio.length === 0 && !loading && (
              <div className="p-12 text-center text-slate-400 text-sm italic">
                列表为空
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Right: Detail View */}
        <div className="col-span-9 bg-slate-50 dark:bg-slate-950 p-6 flex flex-col gap-6 overflow-y-auto">
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
                  <div className="flex items-center gap-3 mt-1">
                    <p className="text-lg font-mono text-slate-500">Price: <span className="text-slate-800 dark:text-slate-200 font-bold">${selectedItem.current_price}</span></p>
                    <span className="text-slate-300">|</span>
                    <p className="text-lg font-mono text-slate-500">Value: <span className="text-blue-600 font-bold">${selectedItem.market_value.toFixed(2)}</span></p>
                  </div>
                </div>
                <Button onClick={handleAnalyze} disabled={analyzing} size="lg" className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 px-8 py-6 text-lg font-bold">
                  <Zap className={clsx("mr-2 h-5 w-5", analyzing && "animate-pulse")} />
                  {analyzing ? "AI 正在分析深度数据..." : "AI 深度分析"}
                </Button>
              </div>

              {/* AI Analysis Cards */}
              <div className="grid gap-6">
                {/* 1. Technical Indicators */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800">
                  <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20"><CardTitle className="text-base font-bold flex items-center gap-2">技术指标 (Technical Analysis)</CardTitle></CardHeader>
                  <CardContent className="pt-4">
                    {aiData ? (
                      <div className="prose dark:prose-invert text-base max-w-none leading-relaxed">
                        <ReactMarkdown>{aiData.technical_analysis}</ReactMarkdown>
                      </div>
                    ) : <div className="text-slate-300 italic text-sm py-4">点击“AI 深度分析”生成报告...</div>}
                  </CardContent>
                </Card>

                {/* 2. Fundamentals */}
                <Card className="shadow-sm border-slate-200 dark:border-slate-800">
                  <CardHeader className="pb-2 border-b bg-slate-50/50 dark:bg-slate-800/20"><CardTitle className="text-base font-bold flex items-center gap-2">基本面和最新消息 (Fundamentals & News)</CardTitle></CardHeader>
                  <CardContent className="pt-4">
                    {aiData ? (
                      <div className="prose dark:prose-invert text-base max-w-none leading-relaxed">
                        <ReactMarkdown>{aiData.fundamental_news}</ReactMarkdown>
                      </div>
                    ) : <div className="text-slate-300 italic text-sm py-4">等待分析中...</div>}
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
            <div className="relative">
              <Input
                placeholder="搜索 (如 AAPL, NVDA)..."
                value={searchQuery}
                onChange={async (e) => {
                  setSearchQuery(e.target.value);
                  setSearching(true);
                  try {
                    const res = await searchStocks(e.target.value);
                    setSearchResults(res);
                  } catch (err) { console.error(err) }
                  finally { setSearching(false); }
                }}
              />
              {searching && <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-slate-400" />}
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
