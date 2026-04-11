"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getStockCapsules,
  refreshStockCapsules,
  type StockCapsulesData,
  type StockCapsuleData,
} from "@/features/analysis/api";

const CAPSULE_STALE_MS = 24 * 60 * 60 * 1000; // 24 hours

function isCapsuleStale(capsule: StockCapsuleData | null): boolean {
  if (!capsule?.updated_at) return true;
  const updatedAt = new Date(capsule.updated_at).getTime();
  return Date.now() - updatedAt > CAPSULE_STALE_MS;
}

interface UseStockCapsuleResult {
  capsules: StockCapsulesData | null;
  newsCapsule: StockCapsuleData | null;
  fundamentalCapsule: StockCapsuleData | null;
  technicalCapsule: StockCapsuleData | null;
  isNewsStale: boolean;
  isFundamentalStale: boolean;
  isTechnicalStale: boolean;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useStockCapsule(ticker: string | null): UseStockCapsuleResult {
  const [capsules, setCapsules] = useState<StockCapsulesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getStockCapsules(ticker);
      setCapsules(data);
    } catch (err) {
      setError("无法加载预分析摘要");
      console.error("useStockCapsule load error:", err);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  const refresh = useCallback(async () => {
    if (!ticker) return;
    setRefreshing(true);
    setError(null);
    try {
      // Step 1: Trigger background refresh (returns immediately with existing capsules)
      await refreshStockCapsules(ticker);

      // Step 2: Poll for updated capsules (check every 3s for up to 90s)
      // The backend generates capsules in background, so we need to poll for the new data
      const pollInterval = setInterval(async () => {
        try {
          const data = await getStockCapsules(ticker);
          setCapsules(data);

          // Stop polling if all capsules have been updated (updated_at within last 60s)
          const now = Date.now();
          const allUpdated = [data.news, data.fundamental, data.technical].every(
            (cap) => cap?.updated_at && now - new Date(cap.updated_at).getTime() < 60000
          );

          if (allUpdated) {
            clearInterval(pollInterval);
          }
        } catch (err) {
          console.error("Polling for capsules failed:", err);
        }
      }, 3000);

      // Auto-stop polling after 90s to prevent infinite loops
      setTimeout(() => clearInterval(pollInterval), 90000);

    } catch (err) {
      setError("刷新预分析摘要失败");
      console.error("useStockCapsule refresh error:", err);
    } finally {
      setRefreshing(false);
    }
  }, [ticker]);

  useEffect(() => {
    setCapsules(null);
    setError(null);
    if (ticker) {
      load();
    }
  }, [ticker, load]);

  const newsCapsule = capsules?.news ?? null;
  const fundamentalCapsule = capsules?.fundamental ?? null;
  const technicalCapsule = capsules?.technical ?? null;

  return {
    capsules,
    newsCapsule,
    fundamentalCapsule,
    technicalCapsule,
    isNewsStale: isCapsuleStale(newsCapsule),
    isFundamentalStale: isCapsuleStale(fundamentalCapsule),
    isTechnicalStale: isCapsuleStale(technicalCapsule),
    loading,
    refreshing,
    error,
    refresh,
  };
}
