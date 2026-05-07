"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";

import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
import { fetchStockSnapshot } from "@/features/market/api";
import type { AnalysisResponse, PortfolioItem } from "@/types";

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
}: AnalysisTabContainerProps) {
  let selectedItem = portfolio.find((item) => item.ticker === selectedTicker) || null;

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
          "flex-1 min-w-0 bg-white dark:bg-slate-950 transition-all duration-300 h-full absolute lg:static w-full inset-y-0 right-0 z-10",
          selectedTicker ? "translate-x-0" : "translate-x-full lg:translate-x-0"
        )}
      >
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
        />
      </div>
    </div>
  );
}
