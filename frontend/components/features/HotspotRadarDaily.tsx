"use client";

import { useState } from "react";
import { TrendingUp, TrendingDown, AlertCircle, RefreshCw, Globe, Zap, ArrowRight, RotateCcw, Layers, CalendarDays, Clock3 } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "@/context/AuthContext";
import type { MacroTopic } from "@/features/dashboard/hooks/useDashboardRadarData";
import type { MarketPulse, TimeLayer } from "@/features/macro/api";
import { formatDateTime } from "@/lib/utils";
import { GlobalNewsFeed } from "./GlobalNewsFeed";

interface HotspotRadarProps {
  loading: boolean;
  onRefresh: (refresh?: boolean) => Promise<void>;
  onSelectTicker: (ticker: string | null) => void;
  topics: MacroTopic[];
}

interface DailyTopicGroup {
  dateKey: string;
  topics: MacroTopic[];
  pulse: MarketPulse | null;
}

const TIME_LAYER_CONFIG: Record<TimeLayer, { label: string; sublabel: string; icon: React.ElementType; badge: string }> = {
  immediate: { label: "即时催化", sublabel: "0-4h", icon: Zap, badge: "bg-amber-500 text-white" },
  narrative: { label: "主题演绎", sublabel: "1-3d", icon: TrendingUp, badge: "bg-blue-500 text-white" },
  cycle: { label: "周期定位", sublabel: "1-4w", icon: Layers, badge: "bg-violet-500 text-white" },
};

const RISK_CFG: Record<string, { bg: string; accent: string; label: string }> = {
  low: { bg: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800/40", accent: "text-emerald-700 dark:text-emerald-400", label: "低风险" },
  medium: { bg: "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-800/40", accent: "text-yellow-700 dark:text-yellow-400", label: "中等风险" },
  high: { bg: "bg-orange-50 border-orange-200 dark:bg-orange-950/20 dark:border-orange-800/40", accent: "text-orange-700 dark:text-orange-400", label: "高风险" },
  extreme: { bg: "bg-rose-50 border-rose-200 dark:bg-rose-950/20 dark:border-rose-800/40", accent: "text-rose-700 dark:text-rose-400", label: "极端风险" },
};

function getDayKey(date: string, timezone: string) {
  return formatDateTime(date, timezone, "YYYY-MM-dd");
}

function getTopicPulse(topic: MacroTopic): MarketPulse | null {
  return topic.impact_analysis?.market_pulse?.one_line ? topic.impact_analysis.market_pulse : null;
}

function buildDailyGroups(topics: MacroTopic[], timezone: string, fallbackPulse: MarketPulse | null): DailyTopicGroup[] {
  const grouped = new Map<string, MacroTopic[]>();
  for (const topic of topics) {
    const key = getDayKey(topic.updated_at, timezone);
    const bucket = grouped.get(key) ?? [];
    bucket.push(topic);
    grouped.set(key, bucket);
  }

  return Array.from(grouped.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([dateKey, dayTopics], index) => {
      const sortedTopics = [...dayTopics].sort((left, right) => {
        if ((right.heat_score ?? 0) !== (left.heat_score ?? 0)) {
          return (right.heat_score ?? 0) - (left.heat_score ?? 0);
        }
        return String(right.updated_at).localeCompare(String(left.updated_at));
      });
      return {
        dateKey,
        topics: sortedTopics.slice(0, 10),
        pulse: sortedTopics.map(getTopicPulse).find(Boolean) ?? (index === 0 ? fallbackPulse : null),
      };
    });
}

function HeatBadge({ score }: { score: number }) {
  const cfg =
    score >= 90 ? { cls: "bg-red-600 text-white", label: "S" } :
    score >= 75 ? { cls: "bg-orange-500 text-white", label: "A" } :
    score >= 60 ? { cls: "bg-amber-400 text-slate-900", label: "B" } :
                  { cls: "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300", label: "C" };

  return (
    <span className={clsx("inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-black tabular-nums", cfg.cls)}>
      {score}
      <span className="text-[9px] opacity-80">{cfg.label}</span>
    </span>
  );
}

function MetaPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
      <span className="font-medium text-slate-400">{label}</span>
      <span className="font-bold text-slate-700 dark:text-slate-100">{value}</span>
    </span>
  );
}

function TickerChip({ ticker, reason, direction, onClick }: {
  ticker: string; reason: string; direction: "bull" | "bear"; onClick: () => void;
}) {
  const isBull = direction === "bull";
  return (
    <button
      onClick={onClick}
      title={reason}
      className={clsx(
        "group inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] transition-colors hover:shadow-sm",
        isBull
          ? "border-emerald-200/60 bg-emerald-50/70 dark:border-emerald-900/40 dark:bg-emerald-950/20"
          : "border-rose-200/60 bg-rose-50/70 dark:border-rose-900/40 dark:bg-rose-950/20"
      )}
    >
      <span className={clsx("font-bold", isBull ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400")}>
        ${ticker}
      </span>
      <span className={clsx("max-w-48 truncate text-[11px]", isBull ? "text-emerald-700/70 dark:text-emerald-500/80" : "text-rose-700/70 dark:text-rose-500/80")}>
        {reason}
      </span>
      <ArrowRight className={clsx("h-2.5 w-2.5 opacity-0 transition-opacity group-hover:opacity-60", isBull ? "text-emerald-600" : "text-rose-600")} />
    </button>
  );
}

function DailyPulsePanel({ pulse }: { pulse: MarketPulse }) {
  const risk = RISK_CFG[pulse.risk_level] ?? RISK_CFG.medium;
  return (
    <div className={clsx("rounded-xl border px-4 py-3", risk.bg)}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Daily Pulse</span>
        <span className={clsx("rounded px-2 py-0.5 text-[11px] font-black", risk.accent, "bg-white/70 dark:bg-black/20")}>
          {risk.label}
        </span>
      </div>
      <p className={clsx("mt-2 text-base font-bold", risk.accent)}>{pulse.one_line}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <MetaPill label="情绪" value={pulse.overall_sentiment} />
        <MetaPill label="利率" value={pulse.rates_direction} />
      </div>
    </div>
  );
}

function DailyEventRow({ topic, index, timezone, onSelectTicker }: {
  topic: MacroTopic; index: number; timezone: string; onSelectTicker: (ticker: string | null) => void;
}) {
  const timeLayer = topic.impact_analysis?.time_layer ?? "narrative";
  const layer = TIME_LAYER_CONFIG[timeLayer] ?? TIME_LAYER_CONFIG.narrative;
  const LayerIcon = layer.icon;
  const beneficiaries = topic.impact_analysis?.beneficiaries ?? [];
  const detriments = topic.impact_analysis?.detriments ?? [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-black text-slate-700 dark:bg-slate-800 dark:text-slate-100">
          {String(index + 1).padStart(2, "0")}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={clsx("inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold", layer.badge)}>
              <LayerIcon className="h-3 w-3" />{layer.label}
            </span>
            <HeatBadge score={topic.heat_score} />
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
              <Clock3 className="h-3 w-3" />{formatDateTime(topic.updated_at, timezone, "HH:mm")}
            </span>
          </div>
          <h3 className="mt-2 text-[15px] font-bold leading-snug text-slate-900 dark:text-slate-100">{topic.title}</h3>
          {topic.summary && (
            <p className="mt-1 text-[12px] leading-relaxed text-slate-500 dark:text-slate-400">{topic.summary}</p>
          )}
          {topic.impact_analysis?.logic && (
            <div className="mt-3 flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-950/50">
              <RotateCcw className="mt-0.5 h-3 w-3 shrink-0 text-slate-400" />
              <p className="text-[12px] leading-relaxed text-slate-500 dark:text-slate-400">{topic.impact_analysis.logic}</p>
            </div>
          )}
          <div className="mt-3 space-y-2">
            {beneficiaries.length > 0 && (
              <div className="flex flex-wrap items-start gap-2">
                <span className="mt-1 inline-flex w-10 shrink-0 items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-500">
                  <TrendingUp className="h-3 w-3" />利好
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {beneficiaries.slice(0, 3).map((item, idx) => (
                    <TickerChip key={`benefit-${topic.id}-${idx}`} ticker={item.ticker} reason={item.reason} direction="bull" onClick={() => onSelectTicker(item.ticker)} />
                  ))}
                </div>
              </div>
            )}
            {detriments.length > 0 && (
              <div className="flex flex-wrap items-start gap-2">
                <span className="mt-1 inline-flex w-10 shrink-0 items-center gap-1 text-[11px] font-bold text-rose-600 dark:text-rose-500">
                  <TrendingDown className="h-3 w-3" />利空
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {detriments.slice(0, 3).map((item, idx) => (
                    <TickerChip key={`detriment-${topic.id}-${idx}`} ticker={item.ticker} reason={item.reason} direction="bear" onClick={() => onSelectTicker(item.ticker)} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DailyDigestCard({ group, timezone, onSelectTicker, isLatest }: {
  group: DailyTopicGroup; timezone: string; onSelectTicker: (ticker: string | null) => void; isLatest: boolean;
}) {
  const topHeat = group.topics[0]?.heat_score ?? 0;

  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-100/70 p-4 dark:border-slate-800 dark:bg-slate-950/30">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] font-black uppercase tracking-widest text-slate-400">
              <CalendarDays className="h-3.5 w-3.5" />Daily Macro Card
            </span>
            {isLatest && (
              <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">最新</span>
            )}
          </div>
          <h2 className="mt-2 text-xl font-bold text-slate-900 dark:text-slate-100">{group.dateKey}</h2>
          <p className="mt-1 text-[12px] text-slate-500 dark:text-slate-400">当日最重要的 {group.topics.length} 个宏观事件，按市场扰动强度排序。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MetaPill label="Top Event" value={group.topics.length > 0 ? group.topics[0].title : "--"} />
          <MetaPill label="事件数" value={String(group.topics.length)} />
          <MetaPill label="峰值热度" value={String(topHeat)} />
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {group.topics.map((topic, index) => (
          <DailyEventRow key={topic.id} topic={topic} index={index} timezone={timezone} onSelectTicker={onSelectTicker} />
        ))}
      </div>
    </section>
  );
}

export function HotspotRadarDaily({ loading, onRefresh, onSelectTicker, topics }: HotspotRadarProps) {
  const { user } = useAuth();
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [scanState, setScanState] = useState<"idle" | "running" | "done" | "failed">("idle");
  const [lastScanAt, setLastScanAt] = useState<string | null>(null);
  const timezone = user?.timezone || "Asia/Shanghai";
  const fallbackPulse = topics.map(getTopicPulse).find(Boolean) ?? null;
  const dailyGroups = buildDailyGroups(topics, timezone, fallbackPulse);
  const latestPulse = dailyGroups[0]?.pulse ?? null;

  const handleManualRefresh = async () => {
    setScanState("running");
    try {
      await onRefresh(true);
      setRefreshNonce((current) => current + 1);
      setLastScanAt(new Date().toISOString());
      setScanState("done");
    } catch (error) {
      console.error("Failed to refresh macro radar", error);
      setScanState("failed");
    }
  };

  const scanStatusText =
    scanState === "running"
      ? "正在扫描全网宏观热点..."
      : scanState === "done" && lastScanAt
        ? `最近一次扫描：${formatDateTime(lastScanAt, timezone, "HH:mm:ss")}`
        : scanState === "failed"
          ? "扫描失败，请稍后重试"
          : "手动扫描会同步更新右侧雷达和左侧快讯流。";

  return (
    <div className="flex h-full flex-col space-y-4 bg-slate-50 p-4 dark:bg-slate-950">
      <div className="flex shrink-0 items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="rounded-lg bg-blue-100 p-1.5 dark:bg-blue-900/30">
            <Globe className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-base font-bold leading-tight text-slate-900 dark:text-slate-100">
              全球宏观雷达
              <span className="ml-2 text-[11px] font-normal text-slate-400">Daily Macro Digest</span>
            </h1>
            <p className="text-[10px] text-slate-500">按交易日聚合宏观事件，优先回答今天最重要的事情是什么、影响哪些资产。</p>
            <p className={clsx(
              "mt-1 text-[10px]",
              scanState === "failed"
                ? "text-rose-500"
                : scanState === "done"
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-slate-400"
            )}>
              {scanStatusText}
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={handleManualRefresh} disabled={loading || scanState === "running"}>
          <RefreshCw className={clsx("mr-1.5 h-3.5 w-3.5", (loading || scanState === "running") && "animate-spin")} />
          {scanState === "running" ? "扫描中..." : "全网扫描热点"}
        </Button>
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-12 gap-4">
        <div className="col-span-12 flex min-h-0 flex-col overflow-hidden lg:col-span-4 xl:col-span-3">
          <GlobalNewsFeed refreshNonce={refreshNonce} />
        </div>
        <div className="col-span-12 flex h-full min-h-0 flex-col lg:col-span-8 xl:col-span-9">
          <div className="shrink-0 rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-slate-400" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">每日宏观热点</h2>
            </div>
            <p className="mt-1 text-[12px] text-slate-500 dark:text-slate-400">按日期输出每日最重要的宏观事件清单，而不是零散主题墙。</p>
          </div>
          <div className="mt-3 custom-scrollbar flex-1 space-y-4 overflow-y-auto pr-1">
            {latestPulse && <DailyPulsePanel pulse={latestPulse} />}
            {dailyGroups.length === 0 && !loading && (
              <div className="rounded-xl border-2 border-dashed border-slate-200 bg-white py-20 text-center dark:border-slate-800 dark:bg-slate-900">
                <AlertCircle className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                <p className="text-sm text-slate-500">暂无可生成的每日宏观卡，请点击「全网扫描热点」</p>
              </div>
            )}
            {dailyGroups.map((group, index) => (
              <DailyDigestCard key={group.dateKey} group={group} timezone={timezone} onSelectTicker={onSelectTicker} isLatest={index === 0} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "outline";
  size?: "sm";
}

function Button({ className, variant, size, children, ...props }: ButtonProps) {
  return (
    <button className={clsx(
      "inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:opacity-50",
      variant === "outline" && "border border-slate-200 bg-white text-slate-900 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800",
      size === "sm" && "h-8 px-3 text-xs",
      className
    )} {...props}>{children}</button>
  );
}