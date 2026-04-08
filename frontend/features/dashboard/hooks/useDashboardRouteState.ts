"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type DashboardTab = "analysis" | "portfolio" | "radar" | "alerts" | "papertrading" | "quant";

const VALID_TABS: DashboardTab[] = ["analysis", "portfolio", "radar", "alerts", "papertrading", "quant"];

export function useDashboardRouteState() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const selectedTicker = searchParams.get("ticker");
  const tab = searchParams.get("tab");
  const activeTab: DashboardTab =
    tab && VALID_TABS.includes(tab as DashboardTab) ? (tab as DashboardTab) : "analysis";

  const selectTicker = (ticker: string | null) => {
    const params = new URLSearchParams(searchParams.toString());

    if (ticker) {
      params.set("ticker", ticker);
      if (activeTab !== "analysis") {
        params.set("tab", "analysis");
      }
    } else {
      params.delete("ticker");
    }

    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const changeTab = (tab: DashboardTab) => {
    if (tab === activeTab) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);

    if (tab !== "analysis") {
      params.delete("ticker");
    } else if (selectedTicker) {
      params.set("ticker", selectedTicker);
    }

    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return {
    activeTab,
    changeTab,
    selectedTicker,
    selectTicker,
  };
}
