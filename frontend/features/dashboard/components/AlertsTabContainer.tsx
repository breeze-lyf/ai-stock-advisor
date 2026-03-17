"use client";

import AlertStream from "@/components/features/AlertStream";
import { useDashboardAlertData } from "@/features/dashboard/hooks/useDashboardAlertData";

export function AlertsTabContainer() {
  const { loading, logs } = useDashboardAlertData();

  return <AlertStream loading={loading} logs={logs} />;
}
