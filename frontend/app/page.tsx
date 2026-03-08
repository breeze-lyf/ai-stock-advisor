"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { PortfolioItem, UserProfile } from "@/types";
import { getPortfolio, analyzeStock, getLatestAnalysis } from "@/lib/api";
import clsx from "clsx";

// Components
import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
import { SearchDialog } from "@/components/features/SearchDialog";
import { PortfolioDashboard } from "@/components/features/PortfolioDashboard";
import { HotspotRadar } from "@/components/features/HotspotRadar";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import AlertStream from "@/components/features/AlertStream";
import { PaperTradingDashboard } from "@/components/features/paper-trading/PaperTradingDashboard";

function DashboardContent() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // --- Core State ---
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTicker, setSelectedTickerState] = useState<string | null>(searchParams.get("ticker"));
  const [activeTab, setActiveTabState] = useState<"analysis" | "portfolio" | "radar" | "alerts" | "papertrading">((searchParams.get("tab") as any) || "analysis");
  const [onlyHoldings, setOnlyHoldings] = useState(false);
  const [news, setNews] = useState<any[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiData, setAiData] = useState<any>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [refreshTimestamp, setRefreshTimestamp] = useState<number>(Date.now());

  // --- URL Sync Logic ---
  const handleSelectTicker = (ticker: string | null) => {
    setSelectedTickerState(ticker);
    const params = new URLSearchParams(searchParams.toString());
    if (ticker) {
      params.set("ticker", ticker);
      // Auto-switch to analysis if a ticker is selected
      if (activeTab !== "analysis") {
        setActiveTabState("analysis");
        params.set("tab", "analysis");
      }
    } else {
      params.delete("ticker");
    }
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const handleTabChange = (tab: "analysis" | "portfolio" | "radar" | "alerts" | "papertrading") => {
    setActiveTabState(tab);
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    if (tab !== "analysis") {
      params.delete("ticker");
    } else if (selectedTicker) {
      params.set("ticker", selectedTicker);
    }
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  // Listen to URL changes (back/forward or external)
  useEffect(() => {
    const tab = searchParams.get("tab") as any;
    const ticker = searchParams.get("ticker");

    if (tab && ["analysis", "portfolio", "radar", "alerts", "papertrading"].includes(tab) && tab !== activeTab) {
      setActiveTabState(tab);
    }
    if (ticker !== selectedTicker) {
      setSelectedTickerState(ticker);
    }
  }, [searchParams]);

  // --- Data Fetching ---
  const fetchData = async (refresh: boolean = false) => {
    if (typeof window === 'undefined' || !localStorage.getItem("token")) return;
    setLoading(true);
    try {
      const data = await getPortfolio(refresh);
      setPortfolio(data);
      if (!user) {
        import("@/lib/api").then(api => api.getProfile()).then(setUser).catch(console.error);
      }
    } catch (error) {
      console.error("Failed to fetch portfolio", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchData(false);
  }, [isAuthenticated]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (typeof window !== 'undefined' && !isAuthenticated && !localStorage.getItem("token")) {
        router.push("/login");
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, router]);

  // Load news and analysis when ticker changes
  useEffect(() => {
    const loadData = async () => {
      if (!selectedTicker) {
        setAiData(null);
        setNews([]);
        return;
      }
      setAiData(null);
      setNews([]);
      try {
        const [analysisResult, newsResult] = await Promise.all([
          getLatestAnalysis(selectedTicker).catch(() => null),
          import("@/lib/api").then(api => api.fetchStockNews(selectedTicker)).catch(() => [])
        ]);
        if (analysisResult) handleParseAnalysis(analysisResult);
        if (newsResult) setNews(newsResult);
      } catch (error) {
        console.error("Failed to load data for", selectedTicker, error);
      }
    };
    loadData();
  }, [selectedTicker, refreshTimestamp]);

  const handleParseAnalysis = (result: any) => {
    if (result.technical_analysis) {
      setAiData(result);
      return;
    }
    try {
      let raw = result.analysis;
      if (!raw) return;
      if (raw.startsWith("```json")) raw = raw.replace("```json", "").replace("```", "");
      const parsed = JSON.parse(raw);
      setAiData({ ...parsed, is_cached: result.is_cached, created_at: result.created_at, model_used: result.model_used });
    } catch (parseErr) {
      setAiData({ technical_analysis: result.analysis, fundamental_news: "Raw output", is_cached: result.is_cached });
    }
  };

  const handleAnalyze = async (force: boolean = false) => {
    if (!selectedTicker) return;
    setAnalyzing(true);
    const startTime = new Date().toISOString();
    try {
      const result = await analyzeStock(selectedTicker, force);
      handleParseAnalysis(result);
      fetchData(false); // Refresh portfolio score
    } catch (error: any) {
      console.warn("Analysis failed, check logs", error);
      // 将报错信息透传到界面上，而不是显示硬编码的“调用失败”
      const errorMsg = error.response?.data?.detail || error.message || "未知错误";
      setAiData({ 
        technical_analysis: `请求失败: ${errorMsg}`, 
        action_advice: "接口请求发生异常，请检查网络或重新登录。", 
        summary_status: "调用失败" 
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRefreshData = async () => {
    setRefreshTimestamp(Date.now());
    await fetchData(false);
  };

  const selectedItem = portfolio.find(p => p.ticker === selectedTicker);

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
      <DashboardHeader 
        user={user} 
        activeTab={activeTab} 
        setActiveTab={(tab: any) => handleTabChange(tab)} 
      />

      <main className="flex-1 min-h-0 relative">
        {activeTab === "analysis" && (
          <div className="flex h-full overflow-hidden">
            <div className={clsx(
              "w-full lg:w-80 shrink-0 border-r dark:border-slate-800 bg-white dark:bg-slate-900 transition-all duration-300 absolute inset-y-0 left-0 lg:static z-20",
              selectedTicker ? "-translate-x-full lg:translate-x-0 lg:block" : "translate-x-0"
            )}>
              <PortfolioList
                portfolio={portfolio}
                selectedTicker={selectedTicker}
                onSelectTicker={handleSelectTicker}
                onRefresh={() => fetchData(false)}
                onOpenSearch={() => setIsSearchOpen(true)}
                onlyHoldings={onlyHoldings}
                onToggleOnlyHoldings={setOnlyHoldings}
              />
            </div>
            <div className={clsx(
              "flex-1 min-w-0 bg-white dark:bg-slate-950 transition-all duration-300 h-full absolute lg:static w-full inset-y-0 right-0 z-10",
              selectedTicker ? "translate-x-0" : "translate-x-full lg:translate-x-0"
            )}>
              <StockDetail
                key={selectedTicker || 'empty'}
                selectedItem={selectedItem || null}
                onAnalyze={handleAnalyze}
                onRefresh={handleRefreshData}
                onBack={() => handleSelectTicker(null)}
                analyzing={analyzing}
                aiData={aiData}
                news={news}
                refreshTimestamp={refreshTimestamp}
              />
            </div>
          </div>
        )}

        {activeTab === "portfolio" && (
          <PortfolioDashboard onSelectTicker={handleSelectTicker} />
        )}

        {activeTab === "radar" && (
          <div className="absolute inset-0 flex flex-col">
            <HotspotRadar onSelectTicker={handleSelectTicker} />
          </div>
        )}

        {activeTab === "alerts" && (
          <div className="absolute inset-0 flex flex-col bg-white dark:bg-slate-950 overflow-y-auto">
            <AlertStream />
          </div>
        )}

        {activeTab === "papertrading" && (
          <div className="absolute inset-0 flex flex-col bg-white dark:bg-slate-950 overflow-y-auto">
            <PaperTradingDashboard />
          </div>
        )}
      </main>

      <SearchDialog
        isOpen={isSearchOpen}
        onOpenChange={setIsSearchOpen}
        onRefresh={() => fetchData(false)}
        onSelectTicker={handleSelectTicker}
        portfolio={portfolio}
      />
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="h-screen w-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
