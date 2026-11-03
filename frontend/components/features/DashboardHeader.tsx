"use client";

import { TrendingUp, PieChart, Globe, Target, BarChart3, Search, Calendar, Bell, Settings, LogOut, Bot, Newspaper, Trophy, Moon, Sun } from "lucide-react";
import { BRAND, FEATURES } from "@/shared/config/features";
import { MarketStatusIndicator } from "@/components/features/MarketStatusIndicator";
import { UserProfile } from "@/types";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";
import clsx from "clsx";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";

export function BrandMark({ className }: { className?: string }) {
  return (
    <div className={clsx("relative flex h-8 w-8 items-center justify-center rounded-md bg-ink text-canvas", className)}>
      <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M4 16l5-5 4 3 7-8" />
        <circle cx="20" cy="6" r="1.6" fill="currentColor" stroke="none" />
      </svg>
    </div>
  );
}

interface NavEntry {
  key: string;
  label: string;
  icon: React.ReactNode;
  href?: string;
  tab?: DashboardTab;
  active: boolean;
}

function NavItem({ item, onTab }: { item: NavEntry; onTab: (t: DashboardTab) => void }) {
  const cls = clsx(
    "relative flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] font-medium whitespace-nowrap transition-colors",
    item.active ? "bg-elevated text-ink" : "text-ink-3 hover:text-ink hover:bg-elevated/60",
  );
  const inner = (
    <>
      <span className={clsx("transition-colors", item.active ? "text-ink" : "")}>{item.icon}</span>
      {item.label}
    </>
  );
  return item.href ? (
    <Link href={item.href} className={cls} aria-current={item.active ? "page" : undefined}>{inner}</Link>
  ) : (
    <button type="button" onClick={() => onTab(item.tab!)} className={cls} aria-current={item.active ? "page" : undefined}>{inner}</button>
  );
}

interface DashboardHeaderProps {
  user: UserProfile | null;
  activeTab: DashboardTab;
  setActiveTab: (tab: DashboardTab) => void;
}

export function DashboardHeader({ user, activeTab, setActiveTab }: DashboardHeaderProps) {
  const pathname = usePathname();
  const cleanPathname = pathname?.endsWith("/") ? pathname.slice(0, -1) : pathname;
  const onDashboard = cleanPathname === "/dashboard";
  const ic = "h-[15px] w-[15px]";
  const items: NavEntry[] = [
    { key: "agent", label: "智能体", icon: <Bot className={ic} />, href: "/", active: cleanPathname === "" || cleanPathname === "/agent" },
    { key: "briefs", label: "简报", icon: <Newspaper className={ic} />, href: "/briefs", active: cleanPathname === "/briefs" },
    { key: "portfolio", label: "持仓与自选", icon: <PieChart className={ic} />, tab: "portfolio", active: onDashboard && activeTab === "portfolio" },
    { key: "analysis", label: "个股诊断", icon: <TrendingUp className={ic} />, tab: "analysis", active: onDashboard && activeTab === "analysis" },
    { key: "review", label: "复盘战绩", icon: <Trophy className={ic} />, href: "/review", active: cleanPathname === "/review" },
    // Hidden by default (see shared/config/features.ts) — not part of the personal-agent core flow.
    ...(FEATURES.radar ? [{ key: "radar", label: "热点", icon: <Globe className={ic} />, tab: "radar" as DashboardTab, active: onDashboard && activeTab === "radar" }] : []),
    ...(FEATURES.paperTrading ? [{ key: "papertrading", label: "模拟", icon: <Target className={ic} />, tab: "papertrading" as DashboardTab, active: onDashboard && activeTab === "papertrading" }] : []),
    ...(FEATURES.calendar ? [{ key: "calendar", label: "日历", icon: <Calendar className={ic} />, href: "/calendar", active: cleanPathname === "/calendar" }] : []),
    ...(FEATURES.quant ? [{ key: "quant", label: "量化", icon: <BarChart3 className={ic} />, href: "/quant", active: cleanPathname === "/quant" }] : []),
    { key: "settings", label: "设置", icon: <Settings className={ic} />, href: "/settings", active: cleanPathname === "/settings" },
  ];

  return (
    <header className="relative z-50 shrink-0 border-b border-line bg-surface/85 backdrop-blur-xl">
      <div className="flex h-14 items-center gap-4 px-4 lg:px-5">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <BrandMark />
          <div className="hidden leading-tight sm:block">
            <p className="text-[14px] font-semibold tracking-tight text-ink">{BRAND.name}</p>
            
          </div>
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-0.5 lg:flex" aria-label="主导航">
          {items.map((it) => <NavItem key={it.key} item={it} onTab={setActiveTab} />)}
        </nav>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <MarketStatusIndicator className="hidden xl:flex" />
          {user && <UserMenuWithAlerts user={user} />}
        </div>
      </div>

      {/* Mobile / tablet: scrollable text tabs */}
      <nav className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden [scrollbar-width:none]" aria-label="主导航">
        {items.map((it) => <NavItem key={it.key} item={it} onTab={setActiveTab} />)}
      </nav>
    </header>
  );
}

function UserMenuWithAlerts({ user }: { user: UserProfile }) {
  const { logout } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const isPro = user.membership_tier === "PRO";
  const itemCls = "group flex h-9 cursor-pointer items-center gap-2.5 rounded-lg px-2.5 text-[13px] text-ink-2 outline-none transition-colors data-[highlighted]:bg-elevated data-[highlighted]:text-ink";

  return (
    <div className="flex items-center gap-2">
      {/* Membership badge (billing UI hidden unless NEXT_PUBLIC_FEATURE_BILLING=true) */}
      {FEATURES.billing && (
        <span className="rounded-full border border-line px-2 py-0.5 text-[10px] font-semibold tracking-wider text-ink-3">{isPro ? "PRO" : "FREE"}</span>
      )}
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button type="button" aria-label="账户菜单" className="rounded-full ring-offset-2 ring-offset-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink">
            <Avatar.Root className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-line bg-elevated">
              <Avatar.Fallback className="text-[11px] font-semibold text-ink-2">{user.email.substring(0, 2).toUpperCase()}</Avatar.Fallback>
            </Avatar.Root>
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content sideOffset={8} align="end" className="z-100 min-w-56 rounded-xl border border-line bg-surface p-1.5 shadow-float animate-in fade-in zoom-in-95 duration-150">
            <div className="mb-1 border-b border-line px-2.5 pb-2 pt-1.5">
              <p className="eyebrow">当前账户</p>
              <p className="mt-0.5 truncate text-[13px] font-medium text-ink">{user.email}</p>
            </div>
            {FEATURES.screener && (
              <DropdownMenu.Item asChild>
                <Link href="/screener" className={itemCls}><Search className="h-4 w-4 text-ink-3" />选股器</Link>
              </DropdownMenu.Item>
            )}
            <DropdownMenu.Item asChild>
              <Link href="/settings" className={itemCls}><Settings className="h-4 w-4 text-ink-3" />设置</Link>
            </DropdownMenu.Item>
            <DropdownMenu.Item asChild>
              <Link href="/dashboard?tab=alerts" className={itemCls}><Bell className="h-4 w-4 text-ink-3" />推送记录</Link>
            </DropdownMenu.Item>
            <DropdownMenu.Item onSelect={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} className={itemCls}>
              {resolvedTheme === "dark" ? <Sun className="h-4 w-4 text-ink-3" /> : <Moon className="h-4 w-4 text-ink-3" />}
              {resolvedTheme === "dark" ? "浅色模式" : "深色模式"}
            </DropdownMenu.Item>
            <DropdownMenu.Separator className="my-1 h-px bg-line" />
            <DropdownMenu.Item onSelect={() => logout()} className={clsx(itemCls, "data-[highlighted]:text-down")}>
              <LogOut className="h-4 w-4 text-ink-3" />退出登录
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
}
