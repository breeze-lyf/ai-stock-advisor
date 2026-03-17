"use client";

import { useRef } from "react";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getMacroRadar } from "@/features/macro/api";

export interface MacroTopic {
  id: string;
  title: string;
  summary: string;
  heat_score: number;
  impact_analysis: {
    logic: string;
    beneficiaries: { ticker: string; reason: string }[];
    detriments: { ticker: string; reason: string }[];
  };
  source_links: string[];
  updated_at: string;
}

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
