"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import Link from 'next/link';

// API
import { PortfolioItem } from "@/types";
import { getPortfolio, analyzeStock } from "@/lib/api";

// Components
import { MarketStatusIndicator } from "@/components/features/MarketStatusIndicator";
import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
import { SearchDialog } from "@/components/features/SearchDialog";

export default function Dashboard() {
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
  const [aiData, setAiData] = useState<{ technical_analysis: string, fundamental_news: string, action_advice: string } | null>(null);

  // UI State
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const fetchData = async (refresh: boolean = false) => {
    if (!localStorage.getItem("token")) return;
    setLoading(true);
    try {
      const data = await getPortfolio(refresh);
      setPortfolio(data);
      // Auto-select first only if no ticker in URL and no current selection
      if (data.length > 0 && !urlTicker && !selectedTicker) {
        setSelectedTicker(data[0].ticker);
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
      if (!isAuthenticated && !localStorage.getItem("token")) {
        router.push("/login");
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, router]);

  useEffect(() => {
    setAiData(null);
  }, [selectedTicker]);

  const handleAnalyze = async () => {
    if (!selectedTicker) return;
    setAnalyzing(true);
    try {
      const result = await analyzeStock(selectedTicker);
      try {
        let raw = result.analysis;
        if (raw.startsWith("```json")) {
          raw = raw.replace("```json", "").replace("```", "");
        }
        const parsed = JSON.parse(raw);
        setAiData(parsed);
      } catch (parseErr) {
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
        <MarketStatusIndicator />
        <div className="ml-auto flex gap-2">
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

      {/* Main Content */}
      <div className="flex-1 min-h-0 grid grid-cols-12 overflow-hidden">
        <PortfolioList
          portfolio={portfolio}
          selectedTicker={selectedTicker}
          onSelectTicker={setSelectedTicker}
          onRefresh={() => fetchData(false)}
          onOpenSearch={() => setIsSearchOpen(true)}
          onlyHoldings={onlyHoldings}
          onToggleOnlyHoldings={setOnlyHoldings}
        />
        <StockDetail
          selectedItem={selectedItem || null}
          onAnalyze={handleAnalyze}
          onRefresh={() => fetchData(false)}
          analyzing={analyzing}
          aiData={aiData}
        />
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
