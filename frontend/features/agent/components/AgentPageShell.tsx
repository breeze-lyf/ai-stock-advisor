"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";

export function AgentPageShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { user } = useDashboardPortfolioData(isAuthenticated);
  const router = useRouter();
  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">
      <DashboardHeader user={user} activeTab={"analysis"} setActiveTab={(tab: DashboardTab) => router.push(`/dashboard?tab=${tab}`)} />
      <main className="flex-1 min-h-0 overflow-y-auto">{children}</main>
    </div>
  );
}
