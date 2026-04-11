"use client";

import { TrendingUp, PieChart, Globe, Target, BarChart3, Search, Calendar, Bell, Settings, LogOut } from "lucide-react";
import { MarketStatusIndicator } from "@/components/features/MarketStatusIndicator";
import { UserProfile } from "@/types";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";
import clsx from "clsx";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";

interface NavItemProps {
  active?: boolean;
  onClick?: () => void;
  href?: string;
  label: string;
  icon: React.ReactNode;
}

function NavItem({ active = false, onClick, href, label, icon }: NavItemProps) {
  const baseClasses = "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap";
  const activeClasses = "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 shadow-sm";
  const inactiveClasses = "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800";

  const content = (
    <>
      <div className={clsx("p-1.5 rounded-md transition-colors", active ? "bg-blue-100 dark:bg-blue-800/30" : "bg-transparent")}>
        {icon}
      </div>
      <span className="hidden lg:block">{label}</span>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={clsx(baseClasses, active ? activeClasses : inactiveClasses)}>
        {content}
      </Link>
    );
  }

  return (
    <button onClick={onClick} className={clsx(baseClasses, active ? activeClasses : inactiveClasses)}>
      {content}
    </button>
  );
}

interface DashboardHeaderProps {
  user: UserProfile | null;
  activeTab: DashboardTab;
  setActiveTab: (tab: DashboardTab) => void;
}

export function DashboardHeader({ user, activeTab, setActiveTab }: DashboardHeaderProps) {
  const pathname = usePathname();
  // Remove trailing slashes for consistent comparison
  const cleanPathname = pathname?.endsWith('/') ? pathname.slice(0, -1) : pathname;
  const isCalendarActive = cleanPathname === "/calendar";
  const isQuantActive = cleanPathname === "/quant";
  const isScreenerActive = cleanPathname === "/screener";

  return (
    <header className="flex h-16 items-center px-4 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl shrink-0 z-50 relative">
      {/* Left Section: Logo + Market Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-linear-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-black text-lg">A</span>
          </div>
          <div className="hidden sm:block">
            <h1 className="font-bold text-base text-slate-900 dark:text-white">AI Stock Advisor</h1>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 -mt-0.5">智能投资助手</p>
          </div>
        </div>

        <MarketStatusIndicator className="hidden lg:flex" />
      </div>

      {/* Center Navigation */}
      <nav className="absolute left-1/2 -translate-x-1/2 hidden xl:flex items-center gap-1">
        <NavItem
          active={activeTab === "analysis" && !isCalendarActive && !isQuantActive && !isScreenerActive}
          onClick={() => setActiveTab("analysis")}
          label="个股"
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <NavItem
          active={activeTab === "portfolio"}
          onClick={() => setActiveTab("portfolio")}
          label="持仓"
          icon={<PieChart className="w-4 h-4" />}
        />
        <NavItem
          active={activeTab === "radar"}
          onClick={() => setActiveTab("radar")}
          label="热点"
          icon={<Globe className="w-4 h-4" />}
        />
        <NavItem
          active={activeTab === "papertrading"}
          onClick={() => setActiveTab("papertrading")}
          label="模拟"
          icon={<Target className="w-4 h-4" />}
        />

        {/* Divider */}
        <div className="w-px h-6 bg-slate-200 dark:bg-slate-700 mx-1" />

        {/* Tool Links */}
        <NavItem
          href="/calendar"
          label="日历"
          icon={<Calendar className="w-4 h-4" />}
          active={isCalendarActive}
        />
        <NavItem
          href="/quant"
          label="量化"
          icon={<BarChart3 className="w-4 h-4" />}
          active={isQuantActive}
        />
      </nav>

      {/* Mobile Nav */}
      <nav className="xl:hidden flex items-center gap-1 ml-auto overflow-x-auto min-w-0 px-2" suppressHydrationWarning>
        <button onClick={() => setActiveTab("analysis")} type="button" className={clsx("p-2 rounded-lg shrink-0 transition-colors", activeTab === "analysis" && !isCalendarActive && !isQuantActive && !isScreenerActive ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500")} title="个股"><TrendingUp className="w-4 h-4" /></button>
        <button onClick={() => setActiveTab("portfolio")} type="button" className={clsx("p-2 rounded-lg shrink-0 transition-colors", activeTab === "portfolio" ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500")} title="持仓"><PieChart className="w-4 h-4" /></button>
        <button onClick={() => setActiveTab("radar")} type="button" className={clsx("p-2 rounded-lg shrink-0 transition-colors", activeTab === "radar" ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500")} title="热点"><Globe className="w-4 h-4" /></button>
        <button onClick={() => setActiveTab("papertrading")} type="button" className={clsx("p-2 rounded-lg shrink-0 transition-colors", activeTab === "papertrading" ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500")} title="模拟"><Target className="w-4 h-4" /></button>
        <div className="w-px h-5 bg-slate-200 dark:bg-slate-700 mx-1 shrink-0" />
        <Link
          href="/calendar"
          className={clsx(
            "p-2 rounded-lg shrink-0",
            isCalendarActive ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500 hover:text-slate-700",
            "transition-colors"
          )}
          title="日历"
          suppressHydrationWarning
        >
          <Calendar className="w-4 h-4" />
        </Link>
        <Link
          href="/quant"
          className={clsx(
            "p-2 rounded-lg shrink-0",
            isQuantActive ? "text-blue-600 bg-blue-50 dark:bg-blue-900/20" : "text-slate-500 hover:text-slate-700",
            "transition-colors"
          )}
          title="量化"
          suppressHydrationWarning
        >
          <BarChart3 className="w-4 h-4" />
        </Link>
      </nav>

      {/* Right Section: User Menu */}
      <div className="ml-auto flex items-center gap-3">
        {user && <UserMenuWithAlerts user={user} />}
      </div>
    </header>
  );
}

interface UserMenuWithAlertsProps {
  user: UserProfile;
}

function UserMenuWithAlerts({ user }: UserMenuWithAlertsProps) {
  const { logout } = useAuth();
  const isPro = user.membership_tier === "PRO";

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="flex items-center gap-3">
      {/* Membership Badge */}
      <div className={clsx(
        "px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-widest uppercase transition-all duration-300 shadow-sm",
        isPro
          ? "bg-slate-900 text-white border border-slate-700 ring-1 ring-slate-800"
          : "bg-slate-100 text-slate-500 border border-slate-200"
      )}>
        {isPro ? "PRO" : "FREE"}
      </div>

      <div className="flex items-center gap-2">
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button type="button" className="flex items-center gap-1.5 focus:outline-none group">
              <div className="relative p-0.5 rounded-full bg-linear-to-tr from-yellow-400 via-rose-600 to-blue-600 animate-gradient-slow shadow-lg group-hover:scale-105 transition-transform duration-300">
                <Avatar.Root className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-slate-100 border-2 border-white dark:border-slate-900 shadow-inner">
                  <Avatar.Image
                    className="h-full w-full object-cover"
                    src="/images/avatar.png"
                    alt={user.email}
                  />
                  <Avatar.Fallback className="flex h-full w-full items-center justify-center bg-slate-100 text-sm font-bold text-slate-500">
                    {user.email.substring(0, 2).toUpperCase()}
                  </Avatar.Fallback>
                </Avatar.Root>
              </div>
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="min-w-55 overflow-hidden rounded-xl bg-white dark:bg-slate-900 p-1.5 shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in fade-in zoom-in-95 duration-200 z-100"
              sideOffset={10}
              align="end"
            >
              <div className="px-3 py-2.5 mb-1.5 border-b border-slate-100 dark:border-slate-800">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Current Account</p>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{user.email}</p>
              </div>

              <DropdownMenu.Item asChild>
                <Link href="/screener" className="group flex h-9 items-center gap-2.5 rounded-lg px-2 text-sm font-medium text-slate-700 outline-none transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                  <Search className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  <span>选股器</span>
                </Link>
              </DropdownMenu.Item>

              <DropdownMenu.Item asChild>
                <Link href="/settings" className="group flex h-9 items-center gap-2.5 rounded-lg px-2 text-sm font-medium text-slate-700 outline-none transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                  <Settings className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  <span>设置</span>
                </Link>
              </DropdownMenu.Item>

              <DropdownMenu.Item asChild>
                <Link href="/alerts" className="group flex h-9 items-center gap-2.5 rounded-lg px-2 text-sm font-medium text-slate-700 outline-none transition-colors hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                  <Bell className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  <span>推送记录</span>
                </Link>
              </DropdownMenu.Item>

            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>

        {/* Independent Logout Button */}
        <button
          onClick={handleLogout}
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-300"
          title="退出登录"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
