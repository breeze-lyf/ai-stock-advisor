"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import QuantDashboard from "@/features/quant/components/QuantDashboard";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";

export default function Page() {
  const { isAuthenticated } = useAuth();
  const { user: userProfile } = useDashboardPortfolioData(isAuthenticated);
  const router = useRouter();

  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
      <DashboardHeader
        user={userProfile}
        activeTab={"quant"}
        setActiveTab={(tab: DashboardTab) => router.push(`/?tab=${tab}`)}
      />
      <main className="flex-1 min-h-0 overflow-y-auto">
        <QuantDashboard standalone />
      </main>
    </div>
  );
}
