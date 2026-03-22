"use client";

import { useRef } from "react";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getMacroRadar, type MacroTopic } from "@/features/macro/api";

export type { MacroTopic } from "@/features/macro/api";

export function useDashboardRadarData() {
  const refreshRequestedRef = useRef(false);
  const { data, loading, refresh } = useCachedResource<MacroTopic[]>({
    cacheEntry: dashboardCache.radar.topics,
    fetcher: () => getMacroRadar(refreshRequestedRef.current),
    onError: (error) => {
      console.error("Failed to fetch macro radar", error);
    },
  });

  return {
    fetchRadar: async (nextRefreshRequested = false) => {
      refreshRequestedRef.current = nextRefreshRequested;
      try {
        await refresh({ showLoading: nextRefreshRequested });
      } finally {
        refreshRequestedRef.current = false;
      }
    },
    loading,
    topics: data || [],
  };
}
