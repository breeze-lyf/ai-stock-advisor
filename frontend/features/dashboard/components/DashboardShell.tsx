"use client";

import type { ReactNode } from "react";

import { DashboardHeader } from "@/components/features/DashboardHeader";
import { SearchDialog } from "@/components/features/SearchDialog";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";
import type { PortfolioItem, UserProfile } from "@/types";

interface DashboardShellProps {
  activeTab: DashboardTab;
  children: ReactNode;
  isSearchOpen: boolean;
  onChangeTab: (tab: DashboardTab) => void;
  onOpenSearchChange: (open: boolean) => void;
  onRefreshSearch: () => void;
  onSelectTicker: (ticker: string | null) => void;
  portfolio: PortfolioItem[];
  user: UserProfile | null;
}

export function DashboardShell({
  activeTab,
  children,
  isSearchOpen,
  onChangeTab,
  onOpenSearchChange,
  onRefreshSearch,
  onSelectTicker,
  portfolio,
  user,
}: DashboardShellProps) {
  return (
    <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
      <DashboardHeader user={user} activeTab={activeTab} setActiveTab={onChangeTab} />
      <main className="flex-1 min-h-0 relative">{children}</main>
      <SearchDialog
        isOpen={isSearchOpen}
        onOpenChange={onOpenSearchChange}
        onRefresh={onRefreshSearch}
        onSelectTicker={onSelectTicker}
        portfolio={portfolio}
      />
    </div>
  );
}
