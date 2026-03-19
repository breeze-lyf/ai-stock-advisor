"use client";

import clsx from "clsx";

import { PortfolioList } from "@/components/features/PortfolioList";
import { StockDetail } from "@/components/features/StockDetail";
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

  // 如果 selectedTicker 存在但不在组合中，创建一个基础对象以便渲染详情页
  if (!selectedItem && selectedTicker) {
    selectedItem = {
      ticker: selectedTicker,
      name: selectedTicker,
      current_price: 0,
      change_percent: 0,
      avg_cost: 0,
      quantity: 0,
      unrealized_pl: 0,
      pl_percent: 0,
      market_value: 0,
    } as any;
  }

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
          selectedItem={selectedItem}
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
