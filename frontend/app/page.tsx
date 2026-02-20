"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import Link from 'next/link';

// API
import { PortfolioItem } from "@/types";
import { getPortfolio, analyzeStock, getLatestAnalysis } from "@/lib/api";
import clsx from "clsx";

// Components
import { MarketStatusIndicator } from "@/components/features/MarketStatusIndicator";
import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
import { SearchDialog } from "@/components/features/SearchDialog";
import { UserMenu } from "@/components/features/UserMenu";
import { UserProfile } from "@/types";

import { Suspense } from "react";

function DashboardContent() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  // URL Sync for selected ticker
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const urlTicker = searchParams.get("ticker");

  // Core State
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTicker, setSelectedTickerState] = useState<string | null>(urlTicker);
  const [onlyHoldings, setOnlyHoldings] = useState(false);

  // News State
  const [news, setNews] = useState<any[]>([]);

  // Synchronize state with URL
  useEffect(() => {
    if (urlTicker && urlTicker !== selectedTicker) {
      setSelectedTickerState(urlTicker);
    }
  }, [urlTicker, selectedTicker]);

  const setSelectedTicker = (ticker: string | null) => {
    setSelectedTickerState(ticker);
    const params = new URLSearchParams(searchParams.toString());
    if (ticker) {
      params.set("ticker", ticker);
    } else {
      params.delete("ticker");
    }
    router.replace(`${pathname}?${params.toString()}`);
  };

  // Analysis State
  const [analyzing, setAnalyzing] = useState(false);
  const [aiData, setAiData] = useState<{
    sentiment_score?: number,
    summary_status?: string,
    risk_level?: string,
    technical_analysis: string,
    fundamental_news: string,
    action_advice: string,
    immediate_action?: string,
    target_price?: number,
    stop_loss_price?: number,
    entry_zone?: string,
    entry_price_low?: number,
    entry_price_high?: number,
    rr_ratio?: string,
    investment_horizon?: string,
    confidence_level?: number,
    is_cached?: boolean,
    created_at?: string,
    model_used?: string
  } | null>(null);

  // UI State
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);

  const fetchData = async (refresh: boolean = false) => {
    if (typeof window === 'undefined' || !localStorage.getItem("token")) return;
    setLoading(true);
    try {
      const data = await getPortfolio(refresh);
      setPortfolio(data);
      // Auto-select first only if no ticker in URL and no current selection
      if (data.length > 0 && !urlTicker && !selectedTicker) {
        setSelectedTicker(data[0].ticker);
      }

      // Fetch user profile if not already loaded
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

      // 切换股票时，先清空旧数据以避免闪烁
      setAiData(null);
      setNews([]);

      try {
        // 并行获取分析和新闻
        const [analysisResult, newsResult] = await Promise.all([
          getLatestAnalysis(selectedTicker).catch(() => null),
          import("@/lib/api").then(api => api.fetchStockNews(selectedTicker)).catch(() => [])
        ]);

        if (analysisResult) {
          handleParseAnalysis(analysisResult);
        }
        if (newsResult) {
          setNews(newsResult);
        }
      } catch (error) {
        console.error("Failed to load data for", selectedTicker, error);
      }
    };

    loadData();
  }, [selectedTicker]);

  const handleParseAnalysis = (result: any) => {
    // 兼容逻辑：如果后端返回的是结构化的结果，直接使用
    if (result.technical_analysis) {
      setAiData({
        sentiment_score: result.sentiment_score,
        summary_status: result.summary_status,
        risk_level: result.risk_level,
        technical_analysis: result.technical_analysis,
        fundamental_news: result.fundamental_news,
        action_advice: result.action_advice,
        immediate_action: result.immediate_action,
        target_price: result.target_price,
        stop_loss_price: result.stop_loss_price,
        entry_zone: result.entry_zone,
        entry_price_low: result.entry_price_low,
        entry_price_high: result.entry_price_high,
        rr_ratio: result.rr_ratio,
        investment_horizon: result.investment_horizon,
        confidence_level: result.confidence_level,
        is_cached: result.is_cached,
        created_at: result.created_at,
        model_used: result.model_used
      });
      return;
    }

    // 后备逻辑：解析旧的 markdown 字符串（如果是存量旧数据）
    try {
      let raw = result.analysis;
      if (!raw) return;
      if (raw.startsWith("```json")) {
        raw = raw.replace("```json", "").replace("```", "");
      }
      const parsed = JSON.parse(raw);
      setAiData({
        ...parsed,
        is_cached: result.is_cached,
        created_at: result.created_at,
        model_used: result.model_used
      });
    } catch (parseErr) {
      setAiData({
        technical_analysis: result.analysis,
        fundamental_news: "Could not parse structured data. Displaying raw output below.",
        action_advice: result.analysis,
        is_cached: result.is_cached,
        created_at: result.created_at,
        model_used: result.model_used
      });
    }
  };

  const handleAnalyze = async (force: boolean = false) => {
    if (!selectedTicker) return;
    setAnalyzing(true);
    const startTime = new Date().toISOString();

    try {
      const result = await analyzeStock(selectedTicker, force);
      handleParseAnalysis(result);

      // 分析完后刷一下新闻和持仓列表 (Refresh news and portfolio after analysis)
      try {
        const newsResult = await import("@/lib/api").then(api => api.fetchStockNews(selectedTicker));
        setNews(newsResult);
        // 重要：刷新持仓列表以更新侧边栏的 R/R 比例 (Sync sidebar RRR)
        fetchData(false);
      } catch (newsError) {
        console.error("News or portfolio refresh failed after analysis:", newsError);
      }
    } catch (error: any) {
      console.warn("Analysis POST request failed/terminated, entering polling recovery mode...", error);

      // 优化容错：轮询机制
      // 很多时候由于网络波动或后端重启，POST 连接断了，但后台 AI 任务可能依然在跑并最终存库
      let recovered = false;
      for (let attempt = 1; attempt <= 5; attempt++) {
        try {
          // 每次重试前等待几秒，给后台处理时间
          await new Promise(resolve => setTimeout(resolve, attempt * 2000));

          const retryResult = await getLatestAnalysis(selectedTicker);
          if (retryResult && retryResult.created_at) {
            // 检查返回的结果是否是本次点击后生成的 (比较时间戳)
            const reportTime = new Date(retryResult.created_at + (retryResult.created_at.includes('Z') ? '' : 'Z')).toISOString();
            if (reportTime >= startTime) {
              console.log(`Successfully recovered analysis data on attempt ${attempt}`);
              handleParseAnalysis(retryResult);
              recovered = true;
              break;
            }
          }
        } catch (retryError) {
          console.error(`Recovery attempt ${attempt} failed:`, retryError);
        }
      }

      if (!recovered) {
        if (error.response?.status === 429) {
          alert("Limit Reached! \ud83d\uded1\nPlease add your own API Key in Settings.");
          router.push("/settings");
        } else {
          alert("Analysis request disconnected. Please check if the diagnosis appears after a few seconds or manually refresh.");
        }
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const selectedItem = portfolio.find(p => p.ticker === selectedTicker);

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-16 items-center px-4 border-b bg-white dark:bg-slate-900 shrink-0 gap-4 z-50 relative">
        <h1 className="font-bold text-lg">AI Investment Advisor</h1>
        <MarketStatusIndicator />
        <div className="ml-auto flex items-center gap-4">
          {user && <UserMenu user={user} />}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 min-h-0 flex overflow-hidden relative">
        <div className={clsx(
          "w-full lg:w-80 shrink-0 border-r dark:border-slate-800 bg-white dark:bg-slate-900 transition-all duration-300 absolute inset-y-0 left-0 lg:static z-20",
          selectedTicker ? "-translate-x-full lg:translate-x-0 lg:block" : "translate-x-0"
        )}>
        <PortfolioList
          portfolio={portfolio}
          selectedTicker={selectedTicker}
          onSelectTicker={setSelectedTicker}
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
            onRefresh={() => fetchData(false)}
            onBack={() => setSelectedTicker(null)}
            analyzing={analyzing}
            aiData={aiData}
            news={news}
          />
        </div>
      </div>

      <SearchDialog
        isOpen={isSearchOpen}
        onOpenChange={setIsSearchOpen}
        onRefresh={() => fetchData(false)}
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
