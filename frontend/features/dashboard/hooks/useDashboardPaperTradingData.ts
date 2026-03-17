"use client";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getSimulatedTrades } from "@/features/paper-trading/api";
import type { SimulatedTrade } from "@/types";

export function useDashboardPaperTradingData() {
  const { data, loading, refresh } = useCachedResource<SimulatedTrade[]>({
    cacheEntry: dashboardCache.paperTrading.trades,
    fetcher: () => getSimulatedTrades(),
    onError: (error) => {
      console.error("Failed to load paper trades", error);
    },
  });

  return {
    loading,
    refreshTrades: refresh,
    trades: data || [],
  };
}
