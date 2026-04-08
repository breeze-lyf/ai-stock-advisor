"use client";

import React, { useState, useEffect } from "react";
import { getSectorExposure, type SectorExposureData, type SectorBreakdown } from "@/features/portfolio/risk-api";
import clsx from "clsx";

// A fixed palette — cycles if there are more than 8 sectors
const SECTOR_COLORS = [
  "#6366f1", // indigo
  "#22d3ee", // cyan
  "#f59e0b", // amber
  "#34d399", // emerald
  "#f87171", // rose
  "#a78bfa", // violet
  "#fb923c", // orange
  "#38bdf8", // sky
];

function riskLevelLabel(level: string) {
  if (level === "HIGH") return { text: "集中度高", cls: "text-rose-500 bg-rose-50 dark:bg-rose-950" };
  if (level === "MEDIUM") return { text: "集中度中", cls: "text-amber-500 bg-amber-50 dark:bg-amber-950" };
  return { text: "分散均衡", cls: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950" };
}

interface SectorBarProps {
  item: SectorBreakdown;
  color: string;
  maxWeight: number;
}

function SectorBar({ item, color, maxWeight }: SectorBarProps) {
  const barWidth = maxWeight > 0 ? (item.weight / maxWeight) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />
      <span className="text-xs text-slate-600 dark:text-slate-300 w-28 truncate">{item.sector}</span>
      <div className="flex-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${barWidth}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs tabular-nums text-slate-500 w-10 text-right">
        {(item.weight * 100).toFixed(1)}%
      </span>
    </div>
  );
}

export function SectorExposurePanel() {
  const [data, setData] = useState<SectorExposureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getSectorExposure()
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setError("暂无持仓数据"); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const risk = data ? riskLevelLabel(data.risk_level) : null;
  const maxWeight = data?.sector_breakdown[0]?.weight ?? 1;

  return (
    <section className="rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-zinc-900 overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="w-1 h-4 rounded-full bg-cyan-500 inline-block" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">组合行业敞口</h3>
          {risk && (
            <span className={clsx("ml-2 text-[10px] font-semibold px-2 py-0.5 rounded-full", risk.cls)}>
              {risk.text}
            </span>
          )}
          <span className="ml-auto text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">Sector Exposure</span>
        </div>
      </div>

      {loading ? (
        <div className="px-5 py-8 text-center text-sm text-slate-400 animate-pulse">加载中…</div>
      ) : error || !data || data.sector_breakdown.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-slate-400">{error || "暂无行业分布数据"}</div>
      ) : (
        <div className="p-5 space-y-5">
          {/* 行业分布条形图 */}
          <div className="space-y-3">
            {data.sector_breakdown.map((item, i) => (
              <SectorBar
                key={item.sector}
                item={item}
                color={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                maxWeight={maxWeight}
              />
            ))}
          </div>

          {/* 集中度指标提示 */}
          <div className="flex gap-3">
            <div className="flex-1 rounded-xl bg-slate-50 dark:bg-zinc-800 px-3 py-2.5 text-center">
              <p className="text-sm font-black tabular-nums text-slate-700 dark:text-slate-200">
                {(data.concentration_ratio * 100).toFixed(0)}%
              </p>
              <p className="text-[10px] text-slate-400 mt-0.5">前3行业占比</p>
            </div>
            <div className="flex-1 rounded-xl bg-slate-50 dark:bg-zinc-800 px-3 py-2.5 text-center">
              <p className="text-sm font-black tabular-nums text-slate-700 dark:text-slate-200">
                {data.herfindahl_index.toFixed(3)}
              </p>
              <p className="text-[10px] text-slate-400 mt-0.5">赫芬达尔指数</p>
            </div>
            <div className="flex-1 rounded-xl bg-slate-50 dark:bg-zinc-800 px-3 py-2.5 text-center">
              <p className="text-sm font-black tabular-nums text-slate-700 dark:text-slate-200">
                {data.sector_breakdown.length}
              </p>
              <p className="text-[10px] text-slate-400 mt-0.5">行业数量</p>
            </div>
          </div>

          {/* 集中度警示线 */}
          {data.concentration_ratio > 0.7 && (
            <div className="flex items-center gap-2 text-xs text-rose-500 bg-rose-50 dark:bg-rose-950/30 rounded-xl px-3 py-2">
              <span>⚠</span>
              前3行业占比超过70%，组合集中度偏高，考虑分散配置
            </div>
          )}
        </div>
      )}
    </section>
  );
}
