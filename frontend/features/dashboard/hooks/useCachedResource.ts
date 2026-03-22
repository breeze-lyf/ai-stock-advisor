"use client";

import { useCallback, useEffect, useState } from "react";

import type { CacheValue, DashboardCacheEntry } from "@/features/dashboard/hooks/dashboardCache";
import {
  readDashboardCache,
  shouldRevalidateDashboardCache,
  writeDashboardCache,
} from "@/features/dashboard/hooks/dashboardCache";

interface RefreshOptions {
  showLoading?: boolean;
}

interface UseCachedResourceOptions<T> {
  cacheEntry: DashboardCacheEntry<T> | null;
  enabled?: boolean;
  fetcher: () => Promise<CacheValue<T>>;
  onError?: (error: unknown) => void;
  refreshIntervalMs?: number;
}

export function useCachedResource<T>({
  cacheEntry,
  enabled = true,
  fetcher,
  onError,
  refreshIntervalMs,
}: UseCachedResourceOptions<T>) {
  const [data, setData] = useState<CacheValue<T>>(cacheEntry ? readDashboardCache(cacheEntry) : null);
  const [loading, setLoading] = useState(cacheEntry ? !readDashboardCache(cacheEntry) : false);

  const refresh = useCallback(async (options?: RefreshOptions) => {
    if (!cacheEntry) {
      setLoading(false);
      return null;
    }

    const shouldShowLoading = options?.showLoading ?? !readDashboardCache(cacheEntry);
    if (shouldShowLoading) {
      setLoading(true);
    }

    try {
      const result = await fetcher();
      setData(writeDashboardCache(cacheEntry, result));
      return result;
    } catch (error) {
      onError?.(error);
      return readDashboardCache(cacheEntry);
    } finally {
      setLoading(false);
    }
  }, [cacheEntry, fetcher, onError]);

  const updateData = useCallback((value: CacheValue<T>) => {
    if (!cacheEntry) {
      setData(value);
      return value;
    }
    setData(writeDashboardCache(cacheEntry, value));
    return value;
  }, [cacheEntry]);

  useEffect(() => {
    if (!cacheEntry) {
      setData(null);
      setLoading(false);
      return;
    }

    setData(readDashboardCache(cacheEntry));
    setLoading(!readDashboardCache(cacheEntry));
  }, [cacheEntry]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    if (!cacheEntry) {
      setLoading(false);
      return;
    }

    if (shouldRevalidateDashboardCache(cacheEntry)) {
      refresh({ showLoading: !readDashboardCache(cacheEntry) });
    } else {
      setLoading(false);
    }

    if (!refreshIntervalMs) {
      return;
    }

    const timer = setInterval(() => {
      refresh({ showLoading: false });
    }, refreshIntervalMs);

    return () => clearInterval(timer);
  }, [cacheEntry, enabled, refresh, refreshIntervalMs]);

  return {
    data,
    loading,
    refresh,
    updateData,
  };
}
