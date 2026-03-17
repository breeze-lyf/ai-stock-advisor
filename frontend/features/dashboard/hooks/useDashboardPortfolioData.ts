"use client";

import { useRef } from "react";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getPortfolio } from "@/features/portfolio/api";
import { getProfile } from "@/features/user/api";
import type { PortfolioItem, UserProfile } from "@/types";

export function useDashboardPortfolioData(isAuthenticated: boolean) {
  const refreshRequestedRef = useRef(false);
  const hasToken = typeof window !== "undefined" && Boolean(localStorage.getItem("token"));
  const enabled = isAuthenticated && hasToken;

  const portfolioResource = useCachedResource<PortfolioItem[]>({
    cacheEntry: dashboardCache.portfolio.items,
    enabled,
    fetcher: () => getPortfolio(refreshRequestedRef.current),
    onError: (error) => {
      console.error("Failed to fetch portfolio", error);
    },
  });
  const userResource = useCachedResource<UserProfile>({
    cacheEntry: dashboardCache.portfolio.user,
    enabled,
    fetcher: () => getProfile(),
    onError: (error) => {
      console.error("Failed to fetch profile", error);
    },
  });

  const fetchPortfolioData = async (refresh = false) => {
    if (!enabled) {
      return;
    }

    refreshRequestedRef.current = refresh;
    try {
      await Promise.all([
        portfolioResource.refresh({ showLoading: true }),
        userResource.data ? Promise.resolve(userResource.data) : userResource.refresh({ showLoading: false }),
      ]);
    } finally {
      refreshRequestedRef.current = false;
    }
  };

  return {
    fetchPortfolioData,
    loading: portfolioResource.loading,
    portfolio: portfolioResource.data || [],
    user: userResource.data,
  };
}
