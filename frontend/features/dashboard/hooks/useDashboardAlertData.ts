"use client";

import { dashboardCache } from "@/features/dashboard/hooks/dashboardCache";
import { useCachedResource } from "@/features/dashboard/hooks/useCachedResource";
import { getNotificationHistory, type NotificationLog } from "@/features/notifications/api";

export function useDashboardAlertData() {
  const { data, loading, refresh } = useCachedResource<NotificationLog[]>({
    cacheEntry: dashboardCache.alerts.logs,
    fetcher: () => getNotificationHistory(30),
    onError: (error) => {
      console.error("Failed to fetch notification history:", error);
    },
    refreshIntervalMs: 30_000,
  });

  return {
    loading,
    logs: data || [],
    refreshAlerts: refresh,
  };
}
