"use client";

import { useState, useEffect } from "react";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { analyzePortfolio, getLatestPortfolioAnalysis } from "@/features/analysis/api";
import { getPortfolioSummary } from "@/features/portfolio/api";
import type { PortfolioAnalysisResponse, PortfolioSummary } from "@/types";

export function useDashboardPortfolioTabData() {
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
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

  // 每日自动刷新持仓分析
  useEffect(() => {
    const checkAndRefreshDailyAnalysis = async () => {
      if (!summaryResource.data) return;

      const lastAnalysis = analysisResource.data;
      if (!lastAnalysis?.created_at) return;

      const lastAnalysisDate = new Date(lastAnalysis.created_at);
      const now = new Date();
      const hoursSinceLastAnalysis = (now.getTime() - lastAnalysisDate.getTime()) / (1000 * 60 * 60);

      // 如果超过 12 小时，自动刷新分析
      if (hoursSinceLastAnalysis >= 12) {
        console.log(`持仓分析已超过 ${hoursSinceLastAnalysis.toFixed(1)} 小时未更新，自动刷新...`);
        await runPortfolioAnalysis();
      }
    };

    checkAndRefreshDailyAnalysis();
  }, [summaryResource.data]);

  const runPortfolioAnalysis = async () => {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const result = await analyzePortfolio();
      analysisResource.updateData(result);
    } catch (error: unknown) {
      console.error("Analysis failed:", error);
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      const detail = axiosErr.response?.data?.detail;
      setAnalyzeError(detail ?? "AI 分析服务暂时不可用，请稍后重试。");
    } finally {
      setAnalyzing(false);
    }
  };

  return {
    analysis: analysisResource.data,
    analyzeError,
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
