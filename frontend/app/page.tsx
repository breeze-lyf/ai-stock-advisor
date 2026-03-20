"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { AnalysisTabContainer } from "@/features/dashboard/components/AnalysisTabContainer";
import { AlertsTabContainer } from "@/features/dashboard/components/AlertsTabContainer";
import { DashboardShell } from "@/features/dashboard/components/DashboardShell";
import { PaperTradingTabContainer } from "@/features/dashboard/components/PaperTradingTabContainer";
import { PortfolioTabContainer } from "@/features/dashboard/components/PortfolioTabContainer";
import {
  type DashboardTab,
  useDashboardRouteState,
} from "@/features/dashboard/hooks/useDashboardRouteState";
import { useDashboardAnalysisData } from "@/features/dashboard/hooks/useDashboardAnalysisData";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import { useDashboardRadarData } from "@/features/dashboard/hooks/useDashboardRadarData";

// Components
import { HotspotRadar } from "@/components/features/HotspotRadar";

function DashboardContent() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [onlyHoldings, setOnlyHoldings] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const { activeTab, changeTab, selectedTicker, selectTicker } = useDashboardRouteState();
  const {
    portfolio,
    fetchPortfolioData,
    user,
  } = useDashboardPortfolioData(isAuthenticated);
  const {
    aiData,
    analyzing,
    news,
    refreshAnalysisData,
    refreshTimestamp,
    runAnalysis,
  } = useDashboardAnalysisData(selectedTicker, fetchPortfolioData);
  const { fetchRadar, loading: radarLoading, topics } = useDashboardRadarData();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleAnalyze = async (force = false) => {
    if (!selectedTicker) {
      return;
    }
    await runAnalysis(selectedTicker, force);
  };

  return (
    <DashboardShell
      user={user}
      activeTab={activeTab}
      onChangeTab={(tab: DashboardTab) => changeTab(tab)}
      isSearchOpen={isSearchOpen}
      onOpenSearchChange={setIsSearchOpen}
      onRefreshSearch={() => fetchPortfolioData(false)}
      onSelectTicker={selectTicker}
      portfolio={portfolio}
    >
        {activeTab === "analysis" && (
          <AnalysisTabContainer
            aiData={aiData}
            analyzing={analyzing}
            news={news}
            onlyHoldings={onlyHoldings}
            onAnalyze={handleAnalyze}
            onOpenSearch={() => setIsSearchOpen(true)}
            onRefreshList={() => fetchPortfolioData(false)}
            onRefreshDetail={refreshAnalysisData}
            onSelectTicker={selectTicker}
            onToggleOnlyHoldings={setOnlyHoldings}
            portfolio={portfolio}
            refreshTimestamp={refreshTimestamp}
            selectedTicker={selectedTicker}
          />
        )}

        {activeTab === "portfolio" && (
          <PortfolioTabContainer onSelectTicker={selectTicker} />
        )}

        {activeTab === "radar" && (
          <div className="absolute inset-0 flex flex-col">
            <HotspotRadar
              loading={radarLoading}
              onRefresh={fetchRadar}
              onSelectTicker={selectTicker}
              topics={topics}
            />
          </div>
        )}

        {activeTab === "alerts" && (
          <div className="absolute inset-0 flex flex-col bg-white dark:bg-slate-950 overflow-y-auto">
            <AlertsTabContainer />
          </div>
        )}

        {activeTab === "papertrading" && (
          <div className="absolute inset-0 flex flex-col bg-white dark:bg-slate-950 overflow-y-auto">
            <PaperTradingTabContainer />
          </div>
        )}
    </DashboardShell>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="h-screen w-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
