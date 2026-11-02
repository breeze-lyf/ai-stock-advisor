"use client";

import { useAuth } from "@/context/AuthContext";
import AgentWorkspace from "@/features/agent/components/AgentWorkspace";
import { Landing } from "@/features/landing/Landing";

/** 登录后首页 = 智能体（对话 + 今日简报 + 持仓异动）；未登录 = 公开落地页。旧仪表盘见 /dashboard。 */
export default function Home() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="h-screen w-screen bg-neutral-50 dark:bg-neutral-950" />;
  return isAuthenticated ? <AgentWorkspace /> : <Landing />;
}
