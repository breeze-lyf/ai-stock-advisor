"use client";

import { useState } from "react";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { analyzePortfolio, getLatestPortfolioAnalysis } from "@/features/analysis/api";
import { getPortfolioSummary } from "@/features/portfolio/api";
import type { PortfolioAnalysisResponse, PortfolioSummary } from "@/types";

export function useDashboardPortfolioTabData() {
  const [analyzing, setAnalyzing] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const summaryResource = useCachedResource<PortfolioSummary>({
    cacheEntry: dashboardCache.portfolioTab.summary,
    fetcher: () => getPortfolioSummary(),
    onError: (error) => {
      console.error("Failed to fetch portfolio data:", error);
    },
  });
  const analysisResource = useCachedResource<PortfolioAnalysisResponse>({
    cacheEntry: dashboardCache.portfolioTab.analysis,
    fetcher: () => getLatestPortfolioAnalysis(),
    onError: (error) => {
      console.error("Analysis background fetch failed:", error);
    },
  });

  const runPortfolioAnalysis = async () => {
    setAnalyzing(true);
    try {
      const result = await analyzePortfolio();
      analysisResource.updateData(result);
    } catch (error) {
      console.error("Analysis failed:", error);
    } finally {
      setAnalyzing(false);
    }
  };

  return {
    analysis: analysisResource.data,
    analyzing,
    fetchPortfolioTabData: async () => {
      await Promise.all([
        summaryResource.refresh({ showLoading: true }),
        analysisResource.refresh({ showLoading: false }),
      ]);
    },
    loading: summaryResource.loading,
    loadingAnalysis: analysisResource.loading && !!summaryResource.data,
    runPortfolioAnalysis,
    setShowReport,
    showReport,
    summary: summaryResource.data,
  };
}
