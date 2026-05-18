"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { Zap } from "lucide-react";

import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
import { fetchStockSnapshot } from "@/features/market/api";
import type { AnalysisResponse, PortfolioItem } from "@/types";
import type { DashboardDetailTab } from "@/features/dashboard/hooks/useDashboardRouteState";

type StockNewsItem = Record<string, unknown>;

interface AnalysisTabContainerProps {
  aiData: AnalysisResponse | null;
  analyzing: boolean;
  news: StockNewsItem[];
  onlyHoldings: boolean;
  onAnalyze: (force?: boolean) => Promise<void>;
  onOpenSearch: () => void;
  onRefreshList: () => void;
  onRefreshDetail: () => Promise<void>;
  onSelectTicker: (ticker: string | null) => void;
  onToggleOnlyHoldings: (value: boolean) => void;
  portfolio: PortfolioItem[];
  refreshTimestamp: number;
  selectedTicker: string | null;
  detailTab: DashboardDetailTab;
  onChangeDetailTab: (tab: DashboardDetailTab) => void;
}

export function AnalysisTabContainer({
  aiData,
  analyzing,
  news,
  onlyHoldings,
  onAnalyze,
  onOpenSearch,
  onRefreshList,
  onRefreshDetail,
  onSelectTicker,
  onToggleOnlyHoldings,
  portfolio,
  refreshTimestamp,
  selectedTicker,
  detailTab,
  onChangeDetailTab,
}: AnalysisTabContainerProps) {
  const [mounted, setMounted] = useState(false);
  let selectedItem = portfolio.find((item) => item.ticker === selectedTicker) || null;

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch snapshot for non-holding stocks
  const [snapshot, setSnapshot] = useState<PortfolioItem | null>(null);
  useEffect(() => {
    if (!selectedTicker) {
      setSnapshot(null);
      return;
    }
    if (selectedItem) {
      setSnapshot(null);
      return;
    }
    let cancelled = false;
    fetchStockSnapshot(selectedTicker)
      .then((data) => { if (!cancelled) setSnapshot(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [selectedTicker, selectedItem]);

  const displayItem = snapshot || selectedItem;

  return (
    <div className="flex h-full overflow-hidden">
      <div
        className={clsx(
          "w-full lg:w-80 shrink-0 border-r dark:border-slate-800 bg-white dark:bg-slate-900 transition-all duration-300 absolute inset-y-0 left-0 lg:static z-20",
          selectedTicker ? "-translate-x-full lg:translate-x-0 lg:block" : "translate-x-0"
        )}
      >
        <PortfolioList
          portfolio={portfolio}
          selectedTicker={selectedTicker}
          onSelectTicker={(ticker) => onSelectTicker(ticker)}
          onRefresh={onRefreshList}
          onOpenSearch={onOpenSearch}
          onlyHoldings={onlyHoldings}
          onToggleOnlyHoldings={onToggleOnlyHoldings}
        />
      </div>
        <div
          className={clsx(
          "flex-1 min-w-0 bg-slate-50 dark:bg-slate-950 transition-all duration-300 h-full absolute lg:static w-full inset-y-0 right-0 z-10",
          selectedTicker ? "translate-x-0" : "translate-x-full lg:translate-x-0"
        )}
      >
        {!mounted ? (
          <div className="flex-1 bg-white dark:bg-zinc-950 p-6 flex flex-col items-center justify-center h-full text-slate-300 gap-4">
            <div className="p-8 rounded-full bg-slate-50 dark:bg-zinc-900 shadow-inner">
              <Zap className="h-16 w-16 opacity-5 animate-pulse" />
            </div>
            <div className="text-center">
              <p className="text-lg font-black text-slate-400 dark:text-slate-600 tracking-tight uppercase">终端就绪</p>
              <p className="text-sm font-medium text-slate-300">请选择一个代码开始深度诊断</p>
            </div>
          </div>
        ) : (
          <StockDetail
            key={selectedTicker || "empty"}
            selectedItem={displayItem}
            onAnalyze={onAnalyze}
            onRefresh={onRefreshDetail}
            onBack={() => onSelectTicker(null)}
            analyzing={analyzing}
            aiData={aiData}
            news={news}
            refreshTimestamp={refreshTimestamp}
            activeTab={detailTab}
            onTabChange={onChangeDetailTab}
          />
        )}
      </div>
    </div>
  );
}
