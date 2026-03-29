"use client";

import { useEffect, useRef } from "react";

import {
  dashboardCache,
  getOrCreateDashboardCacheEntry,
  readDashboardCache,
} from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getAnalysisHistory } from "@/features/analysis/api";
import { fetchStockHistory } from "@/features/market/api";
import type { AnalysisResponse } from "@/types";

const STOCK_HISTORY_TTL_MS = 10 * 60_000;
const ANALYSIS_HISTORY_TTL_MS = 10 * 60_000;
const EMPTY_ARRAY: unknown[] = [];


export function useDashboardStockDetailData(
  selectedTicker: string | null,
  refreshTimestamp?: number
) {
  const lastRefreshTimestampRef = useRef<number | undefined>(refreshTimestamp);
  const stockHistoryEntry = selectedTicker
    ? getOrCreateDashboardCacheEntry(dashboardCache.market.historyByTicker, selectedTicker, STOCK_HISTORY_TTL_MS)
    : null;
  const analysisHistoryEntry = selectedTicker
    ? getOrCreateDashboardCacheEntry(
        dashboardCache.analysis.historyByTicker,
        selectedTicker,
        ANALYSIS_HISTORY_TTL_MS
      )
    : null;

  const stockHistoryResource = useCachedResource<unknown[]>({
    cacheEntry: stockHistoryEntry,
    enabled: Boolean(selectedTicker),
    fetcher: async () => {
      const latest = await fetchStockHistory(selectedTicker!);
      const cached = stockHistoryEntry ? readDashboardCache(stockHistoryEntry) : null;
      // 防止上游偶发空返回把已有图表清空（表现为“K线闪一下就消失”）
      if (
        Array.isArray(latest) &&
        latest.length === 0 &&
        Array.isArray(cached) &&
        cached.length > 0
      ) {
        return cached as unknown[];
      }
      return latest;
    },
    onError: (error) => {
      console.error("Failed to fetch stock history for", selectedTicker, error);
    },
    shouldRevalidate: (cached) => !Array.isArray(cached) || cached.length === 0,
  });
  const analysisHistoryResource = useCachedResource<AnalysisResponse[]>({
    cacheEntry: analysisHistoryEntry,
    enabled: Boolean(selectedTicker),
    fetcher: () => getAnalysisHistory(selectedTicker!),
    onError: (error) => {
      console.error("Failed to fetch analysis history for", selectedTicker, error);
    },
  });

  useEffect(() => {
    if (!selectedTicker || refreshTimestamp === undefined) {
      return;
    }

    if (lastRefreshTimestampRef.current === refreshTimestamp) {
      return;
    }

    lastRefreshTimestampRef.current = refreshTimestamp;

    void Promise.all([
      stockHistoryResource.refresh({ showLoading: true }),
      analysisHistoryResource.refresh({ showLoading: false }),
    ]);
  }, [analysisHistoryResource, refreshTimestamp, selectedTicker, stockHistoryResource]);

  useEffect(() => {
    if (!selectedTicker) return;
    console.debug("[history] ticker=%s loading=%s len=%s", selectedTicker, stockHistoryResource.loading, Array.isArray(stockHistoryResource.data) ? stockHistoryResource.data.length : "null");
  }, [selectedTicker, stockHistoryResource.data, stockHistoryResource.loading]);

  return {
    analysisHistory: analysisHistoryResource.data || EMPTY_ARRAY,
    historyData: stockHistoryResource.data || EMPTY_ARRAY,

    historyLoading: stockHistoryResource.loading || analysisHistoryResource.loading,
    refreshHistoryData: async () => {
      await Promise.all([
        stockHistoryResource.refresh({ showLoading: true }),
        analysisHistoryResource.refresh({ showLoading: false }),
      ]);
    },
  };
}
