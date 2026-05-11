"use client";

import React from "react";
import Link from "next/link";
import {
  Bell,
  BellRing,
  Calendar,
  ChevronRight,
  Clock3,
  Gauge,
  Globe2,
  Radar,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import type { NotificationLog } from "@/features/notifications/api";
import { formatDateTime } from "@/lib/utils";

interface AlertStreamProps {
  loading: boolean;
  logs: NotificationLog[];
}

type AlertMeta = {
  label: string;
  summary: string;
  accent: string;
  badge: string;
  icon: React.ReactNode;
};

function normalizeType(type: string) {
  return (type || "general").trim().toLowerCase();
}

function getAlertMeta(log: NotificationLog): AlertMeta {
  const normalizedType = normalizeType(log.type);
  const priority = (log.priority || "P2").toUpperCase();

  if (normalizedType === "price_alert") {
    return {
      label: "价格预警",
      summary: "适合第一时间处理的关键价位提醒",
      accent: "border-emerald-200 bg-emerald-50/80 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300",
      badge: priority,
      icon: <TrendingUp className="h-4 w-4" />,
    };
  }

  if (normalizedType === "indicator_alert") {
    return {
      label: "技术指标提醒",
      summary: "适合盯盘型用户的补充型信号",
      accent: "border-amber-200 bg-amber-50/80 text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300",
      badge: priority,
      icon: <Gauge className="h-4 w-4" />,
    };
  }

  if (normalizedType === "macro_alert" || normalizedType === "macro_summary") {
    return {
      label: normalizedType === "macro_alert" ? "宏观重大事件" : "宏观汇总",
      summary: "帮助你快速判断外部环境是否值得切换注意力",
      accent: "border-sky-200 bg-sky-50/80 text-sky-700 dark:border-sky-900/40 dark:bg-sky-950/20 dark:text-sky-300",
      badge: priority,
      icon: normalizedType === "macro_alert" ? <Globe2 className="h-4 w-4" /> : <Radar className="h-4 w-4" />,
    };
  }

  if (normalizedType === "strategy_change") {
    return {
      label: "策略变更",
      summary: "当判断方向有明显变化时，帮助你重新看一眼仓位",
      accent: "border-violet-200 bg-violet-50/80 text-violet-700 dark:border-violet-900/40 dark:bg-violet-950/20 dark:text-violet-300",
      badge: priority,
      icon: <Sparkles className="h-4 w-4" />,
    };
  }

  if (normalizedType === "daily_report" || normalizedType === "hourly_news_summary") {
    return {
      label: normalizedType === "daily_report" ? "每日复盘" : "整点摘要",
      summary: "更适合集中查看，而不是要求你立刻处理",
      accent: "border-slate-200 bg-slate-50/80 text-slate-700 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-300",
      badge: priority,
      icon: <Calendar className="h-4 w-4" />,
    };
  }

  return {
    label: "系统通知",
    summary: "用于补充状态同步与测试反馈",
    accent: "border-slate-200 bg-slate-50/80 text-slate-700 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-300",
    badge: priority,
    icon: <Bell className="h-4 w-4" />,
  };
}

function formatRelativeBucket(dateString: string) {
  const createdAt = new Date(dateString).getTime();
  const diffMs = Date.now() - createdAt;
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 6) return "最近 6 小时";
  if (diffHours < 24) return "最近 24 小时";
  if (diffHours < 72) return "最近 3 天";
  return "更早";
}

const AlertStream: React.FC<AlertStreamProps> = ({ loading, logs }) => {
  const { user } = useAuth();
  const priceAlertCount = logs.filter((log) => normalizeType(log.type) === "price_alert").length;
  const strategyChangeCount = logs.filter((log) => normalizeType(log.type) === "strategy_change").length;
  const highPriorityCount = logs.filter((log) => ["P0", "P1"].includes((log.priority || "").toUpperCase())).length;

  if (loading) {
    return (
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 md:px-6">
        <div className="h-28 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-24 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
          ))}
        </div>
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-40 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
          ))}
        </div>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col items-center px-4 py-16 text-center md:px-6">
        <div className="rounded-full border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <BellRing className="h-8 w-8 text-slate-400" />
        </div>
        <h2 className="mt-6 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">通知中心还很安静</h2>
        <p className="mt-3 max-w-xl text-sm leading-6 text-slate-500 dark:text-slate-400">
          这通常说明你的策略还没有触发需要处理的提醒，或者通知渠道还没完全连上。先把最关键的几类提醒配置好，后面这里就会更像你的决策时间线。
        </p>
        <Link
          href="/settings"
          className="mt-6 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:text-slate-100"
        >
          去完善通知设置
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:px-6 md:py-8">
      <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-emerald-50/70 p-6 shadow-sm dark:border-slate-800 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950/20">
        <div className="flex flex-col gap-5 2xl:flex-row 2xl:items-end 2xl:justify-between">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-700 dark:border-emerald-900/40 dark:bg-slate-950/50 dark:text-emerald-300">
              <BellRing className="h-3.5 w-3.5" />
              通知中心
            </div>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">提醒应该先告诉你轻重，再告诉你细节</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              这里收的是已经发给你的历史提醒。我们按“值得立即处理”到“适合稍后浏览”的思路来呈现，让提醒流和设置页的使用逻辑保持一致。
            </p>
          </div>

          <div className="grid w-full gap-3 min-[520px]:grid-cols-3 2xl:w-auto">
            <div className="min-w-0 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70 2xl:min-w-[128px]">
              <div className="text-xs text-slate-500 dark:text-slate-400">高优先级提醒</div>
              <div className="mt-1 whitespace-nowrap text-2xl font-semibold text-slate-900 dark:text-slate-100">{highPriorityCount}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70 2xl:min-w-[128px]">
              <div className="text-xs text-slate-500 dark:text-slate-400">价格类提醒</div>
              <div className="mt-1 whitespace-nowrap text-2xl font-semibold text-slate-900 dark:text-slate-100">{priceAlertCount}</div>
            </div>
            <div className="min-w-0 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70 2xl:min-w-[128px]">
              <div className="text-xs text-slate-500 dark:text-slate-400">策略变化</div>
              <div className="mt-1 whitespace-nowrap text-2xl font-semibold text-slate-900 dark:text-slate-100">{strategyChangeCount}</div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">最近一条提醒</div>
          <div className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{logs[0]?.title || "暂无"}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">最近活跃时段</div>
          <div className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{formatRelativeBucket(logs[0]?.created_at || new Date().toISOString())}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">通知设置</div>
          <Link href="/settings" className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-emerald-700 hover:text-emerald-800 dark:text-emerald-300 dark:hover:text-emerald-200">
            去调整提醒策略
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      <div className="space-y-4">
        {logs.map((log) => {
          const meta = getAlertMeta(log);

          return (
            <article
              key={log.id}
              className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${meta.accent}`}>
                      {meta.icon}
                      {meta.label}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
                      {meta.badge || "P2"}
                    </span>
                    {(log.ticker || log.target_id) && (
                      <span className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 dark:border-slate-800 dark:text-slate-400">
                        {log.ticker || log.target_id}
                      </span>
                    )}
                  </div>

                  <h3 className="mt-4 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">{log.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{meta.summary}</p>
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700 dark:text-slate-300">{log.content}</p>
                </div>

                <div className="flex shrink-0 flex-col gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm dark:border-slate-800 dark:bg-slate-950/70 lg:min-w-[240px]">
                  <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                    <Clock3 className="h-4 w-4" />
                    {formatDateTime(log.created_at, user?.timezone || "Asia/Shanghai")}
                  </div>
                  <div className="text-xs leading-5 text-slate-500 dark:text-slate-400">
                    {["P0", "P1"].includes((log.priority || "").toUpperCase())
                      ? "这类提醒更偏向需要尽快处理。"
                      : "这类提醒更适合成批浏览或稍后复盘。"}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
};

export default AlertStream;
