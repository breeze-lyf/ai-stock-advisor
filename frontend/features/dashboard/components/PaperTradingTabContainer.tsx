"use client";

import { PaperTradingDashboard } from "@/components/features/paper-trading/PaperTradingDashboard";
import { useDashboardPaperTradingData } from "@/features/dashboard/hooks/useDashboardPaperTradingData";

export function PaperTradingTabContainer() {
  const { loading, trades } = useDashboardPaperTradingData();

  return <PaperTradingDashboard loading={loading} trades={trades} />;
}
