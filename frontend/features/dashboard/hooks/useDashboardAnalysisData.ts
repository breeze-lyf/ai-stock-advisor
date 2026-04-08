"use client";

import { useState } from "react";
import axios from "axios";

import {
  dashboardCache,
  getOrCreateDashboardCacheEntry,
} from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { analyzeStock, getLatestAnalysis } from "@/features/analysis/api";
import { fetchStockNews } from "@/features/portfolio/api";
import type { AnalysisResponse } from "@/types";

type StockNewsItem = Record<string, unknown>;

const ANALYSIS_TTL_MS = 10 * 60_000;
const NEWS_TTL_MS = 12 * 60 * 60_000; // 12 hours

export function useDashboardAnalysisData(
  selectedTicker: string | null,
  refreshPortfolio: (refresh?: boolean) => Promise<void>
) {
  const [analyzing, setAnalyzing] = useState(false);
  const [refreshTimestamp, setRefreshTimestamp] = useState<number>(Date.now());
  const analysisEntry = selectedTicker
    ? getOrCreateDashboardCacheEntry(dashboardCache.analysis.byTicker, selectedTicker, ANALYSIS_TTL_MS)
    : null;
  const newsEntry = selectedTicker
    ? getOrCreateDashboardCacheEntry(dashboardCache.analysis.newsByTicker, selectedTicker, NEWS_TTL_MS)
    : null;
  const analysisResource = useCachedResource<AnalysisResponse>({
    cacheEntry: analysisEntry,
    enabled: Boolean(selectedTicker),
    fetcher: () => getLatestAnalysis(selectedTicker!),
    onError: (error) => {
      console.error("Failed to load analysis for", selectedTicker, error);
    },
  });
  const newsResource = useCachedResource<StockNewsItem[]>({
    cacheEntry: newsEntry,
    enabled: Boolean(selectedTicker),
    fetcher: () => fetchStockNews(selectedTicker!),
    onError: (error) => {
      console.error("Failed to load news for", selectedTicker, error);
    },
  });

  const runAnalysis = async (ticker: string, force = false) => {
    setAnalyzing(true);
    try {
      const result = await analyzeStock(ticker, force);
      analysisResource.updateData(result);
      await refreshPortfolio(false);
    } catch (error: unknown) {
      const errorMsg = axios.isAxiosError(error)
        ? (error.response?.data?.detail || error.message || "未知错误")
        : (error instanceof Error ? error.message : "未知错误");
      const isQuotaLimit = axios.isAxiosError(error) && error.response?.status === 429;
      analysisResource.updateData({
        ticker,
        technical_analysis: `请求失败: ${errorMsg}`,
        action_advice: isQuotaLimit
          ? "免费额度已用完。请在设置中配置个人 API Key，或稍后再试。"
          : "接口请求发生异常，请检查网络或重新登录。",
        summary_status: "调用失败",
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const refreshAnalysisData = async () => {
    setRefreshTimestamp(Date.now());
    await Promise.all([
      analysisResource.refresh({ showLoading: true }),
      newsResource.refresh({ showLoading: true }),
      refreshPortfolio(false),
    ]);
  };

  return {
    aiData: analysisResource.data,
    analyzing,
    news: newsResource.data || [],
    refreshAnalysisData,
    refreshTimestamp,
    runAnalysis,
  };
}
