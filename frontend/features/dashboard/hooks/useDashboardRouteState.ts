"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type DashboardTab = "analysis" | "portfolio" | "radar" | "alerts" | "papertrading" | "quant";
export type DashboardDetailTab = "info" | "analysis";

const VALID_TABS: DashboardTab[] = ["analysis", "portfolio", "radar", "alerts", "papertrading", "quant"];

export function useDashboardRouteState() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const clientSearch =
    typeof window !== "undefined" ? window.location.search : `?${searchParams.toString()}`;
  const effectiveParams = new URLSearchParams(
    clientSearch.startsWith("?") ? clientSearch.slice(1) : clientSearch
  );

  const selectedTicker = effectiveParams.get("ticker");
  const tab = effectiveParams.get("tab");
  const detail = effectiveParams.get("detail");
  const activeTab: DashboardTab =
    tab && VALID_TABS.includes(tab as DashboardTab) ? (tab as DashboardTab) : "analysis";
  const detailTab: DashboardDetailTab = detail === "analysis" ? "analysis" : "info";

  const selectTicker = (ticker: string | null) => {
    const params = new URLSearchParams(effectiveParams.toString());

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
    const params = new URLSearchParams(effectiveParams.toString());
    params.set("tab", tab);

    if (tab !== "analysis") {
      params.delete("ticker");
    } else if (selectedTicker) {
      params.set("ticker", selectedTicker);
    }

    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  const changeDetailTab = (nextDetailTab: DashboardDetailTab) => {
    const params = new URLSearchParams(effectiveParams.toString());

    if (nextDetailTab === "analysis") {
      params.set("detail", "analysis");
    } else {
      params.delete("detail");
    }

    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return {
    activeTab,
    detailTab,
    changeTab,
    changeDetailTab,
    selectedTicker,
    selectTicker,
  };
}
