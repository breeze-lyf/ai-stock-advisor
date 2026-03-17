"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type DashboardTab = "analysis" | "portfolio" | "radar" | "alerts" | "papertrading";

const VALID_TABS: DashboardTab[] = ["analysis", "portfolio", "radar", "alerts", "papertrading"];

export function useDashboardRouteState() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const [selectedTicker, setSelectedTickerState] = useState<string | null>(searchParams.get("ticker"));
  const [activeTab, setActiveTabState] = useState<DashboardTab>(
    VALID_TABS.includes(searchParams.get("tab") as DashboardTab)
      ? (searchParams.get("tab") as DashboardTab)
      : "analysis"
  );

  useEffect(() => {
    const tab = searchParams.get("tab");
    const ticker = searchParams.get("ticker");

    if (tab && VALID_TABS.includes(tab as DashboardTab) && tab !== activeTab) {
      setActiveTabState(tab as DashboardTab);
    }

    if (ticker !== selectedTicker) {
      setSelectedTickerState(ticker);
    }
  }, [activeTab, searchParams, selectedTicker]);

  const selectTicker = (ticker: string | null) => {
    setSelectedTickerState(ticker);
    const params = new URLSearchParams(searchParams.toString());

    if (ticker) {
      params.set("ticker", ticker);
      if (activeTab !== "analysis") {
        setActiveTabState("analysis");
        params.set("tab", "analysis");
      }
    } else {
      params.delete("ticker");
    }

    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const changeTab = (tab: DashboardTab) => {
    setActiveTabState(tab);
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);

    if (tab !== "analysis") {
      params.delete("ticker");
    } else if (selectedTicker) {
      params.set("ticker", selectedTicker);
    }

    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return {
    activeTab,
    changeTab,
    selectedTicker,
    selectTicker,
  };
}
