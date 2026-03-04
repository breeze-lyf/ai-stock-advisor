"use client";

import { TrendingUp, PieChart, Globe, Bell } from "lucide-react";
import { MarketStatusIndicator } from "@/components/features/MarketStatusIndicator";
import { UserMenu } from "@/components/features/UserMenu";
import { UserProfile } from "@/types";
import clsx from "clsx";

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}

function TabButton({ active, onClick, label, icon }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-bold transition-all",
        active 
          ? "bg-white dark:bg-slate-700 text-blue-600 shadow-sm" 
          : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

interface DashboardHeaderProps {
  user: UserProfile | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export function DashboardHeader({ user, activeTab, setActiveTab }: DashboardHeaderProps) {
  return (
    <header className="flex h-16 items-center px-4 border-b bg-white dark:bg-slate-900 shrink-0 gap-4 z-50 relative">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-black text-xl">A</span>
          </div>
          <h1 className="font-bold text-lg hidden sm:block">AI Stock Advisor</h1>
        </div>
        
        {/* Market Status back to Left side */}
        <MarketStatusIndicator className="hidden md:flex" />
      </div>
      
      {/* Navigation Tabs - Centered */}
      <nav className="absolute left-1/2 -translate-x-1/2 hidden lg:flex items-center gap-1 h-10 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
        <TabButton 
          active={activeTab === "analysis"} 
          onClick={() => setActiveTab("analysis")}
          label="个股诊断"
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <TabButton 
          active={activeTab === "portfolio"} 
          onClick={() => setActiveTab("portfolio")}
          label="我的持仓"
          icon={<PieChart className="w-4 h-4" />}
        />
        <TabButton 
          active={activeTab === "radar"} 
          onClick={() => setActiveTab("radar")}
          label="全球热点"
          icon={<Globe className="w-4 h-4" />}
        />
        <TabButton 
          active={activeTab === "alerts"} 
          onClick={() => setActiveTab("alerts")}
          label="智能提醒"
          icon={<Bell className="w-4 h-4" />}
        />
      </nav>

      {/* Mobile Nav Fallback (relative when absolute tab is hidden) */}
      <nav className="lg:hidden flex items-center gap-1 h-10 bg-slate-100 dark:bg-slate-800 p-0.5 rounded-xl ml-2 overflow-x-auto min-w-0">
         <button onClick={() => setActiveTab("analysis")} className={clsx("p-2 rounded-lg", activeTab === "analysis" ? "text-blue-600 bg-white" : "text-slate-500")} title="诊断"><TrendingUp className="w-4 h-4" /></button>
         <button onClick={() => setActiveTab("portfolio")} className={clsx("p-2 rounded-lg", activeTab === "portfolio" ? "text-blue-600 bg-white" : "text-slate-500")} title="持仓"><PieChart className="w-4 h-4" /></button>
         <button onClick={() => setActiveTab("radar")} className={clsx("p-2 rounded-lg", activeTab === "radar" ? "text-blue-600 bg-white" : "text-slate-500")} title="热点"><Globe className="w-4 h-4" /></button>
         <button onClick={() => setActiveTab("alerts")} className={clsx("p-2 rounded-lg", activeTab === "alerts" ? "text-blue-600 bg-white" : "text-slate-500")} title="提醒"><Bell className="w-4 h-4" /></button>
      </nav>

      <div className="ml-auto flex items-center gap-4">
        {user && <UserMenu user={user} />}
      </div>
    </header>
  );
}
