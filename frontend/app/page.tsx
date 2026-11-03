"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import AgentWorkspace from "@/features/agent/components/AgentWorkspace";

/** 登录后首页 = 智能体（对话 + 今日简报 + 持仓异动）；未登录跳转到原登录/介绍页。旧仪表盘见 /dashboard。 */
export default function Home() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !isAuthenticated) router.replace("/login");
  }, [loading, isAuthenticated, router]);
  if (loading || !isAuthenticated) return <div className="h-screen w-screen bg-neutral-50 dark:bg-neutral-950" />;
  return <AgentWorkspace />;
}
