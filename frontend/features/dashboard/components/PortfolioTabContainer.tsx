"use client";

import { PortfolioDashboard } from "@/components/features/PortfolioDashboard";
import { useDashboardPortfolioTabData } from "@/features/dashboard/hooks/useDashboardPortfolioTabData";

interface PortfolioTabContainerProps {
  onSelectTicker: (ticker: string | null) => void;
}

export function PortfolioTabContainer({ onSelectTicker }: PortfolioTabContainerProps) {
  const {
    analysis,
    analyzeError,
    analyzing,
    loading,
    loadingAnalysis,
    runPortfolioAnalysis,
    setShowReport,
    showReport,
    summary,
  } = useDashboardPortfolioTabData();

  return (
    <PortfolioDashboard
      analysis={analysis}
      analyzeError={analyzeError}
      analyzing={analyzing}
      loading={loading}
      loadingAnalysis={loadingAnalysis}
      onAnalyze={runPortfolioAnalysis}
      onSelectTicker={onSelectTicker}
      onShowReportChange={setShowReport}
      showReport={showReport}
      summary={summary}
    />
  );
}
