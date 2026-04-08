"use client";

import React, { useState, useEffect } from "react";
import { getSignals, getSignalPerformance, type SignalItem, type SignalPerformance } from "@/features/analysis/signals-api";
import clsx from "clsx";

interface SignalPerformanceProps {
  ticker: string;
}

const SIGNAL_TYPE_LABEL: Record<string, string> = {
  BUY: "买入",
  SELL: "卖出",
  HOLD: "持有",
  WATCH: "观察",
};

const SIGNAL_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "活跃",
  CLOSED: "已关闭",
  EXPIRED: "已过期",
  CANCELLED: "已取消",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function SignalPerformancePanel({ ticker }: SignalPerformanceProps) {
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [performance, setPerformance] = useState<SignalPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSignals([]);
    setPerformance(null);

    Promise.all([
      getSignals(ticker, 6),
      getSignalPerformance("ALL"),
    ])
      .then(([sigs, perf]) => {
        if (cancelled) return;
        setSignals(sigs);
        setPerformance(perf);
      })
      .catch(() => {
        if (!cancelled) setError("暂无信号数据");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [ticker]);

  return (
    <section className="rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-zinc-900 overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="w-1 h-4 rounded-full bg-violet-500 inline-block" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">历史信号命中率</h3>
          <span className="ml-auto text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">Signal Performance</span>
        </div>
      </div>

      {loading ? (
        <div className="px-5 py-8 text-center text-sm text-slate-400 animate-pulse">加载中…</div>
      ) : error ? (
        <div className="px-5 py-8 text-center text-sm text-slate-400">{error}</div>
      ) : (
        <div className="p-5 space-y-5">
          {/* 统计指标行 */}
          {performance && (
            <div className="grid grid-cols-3 gap-3">
              <StatCell
                label="整体胜率"
                value={`${performance.win_rate.toFixed(1)}%`}
                color={performance.win_rate >= 50 ? "emerald" : "rose"}
              />
              <StatCell
                label="已关闭信号"
                value={String(performance.closed_signals)}
                color="slate"
              />
              <StatCell
                label="平均盈亏"
                value={`${performance.avg_pnl_percent >= 0 ? "+" : ""}${performance.avg_pnl_percent.toFixed(1)}%`}
                color={performance.avg_pnl_percent >= 0 ? "emerald" : "rose"}
              />
            </div>
          )}

          {/* 胜率可视化 */}
          {performance && performance.closed_signals > 0 && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>盈利 {performance.winning_signals} 笔</span>
                <span>亏损 {performance.losing_signals} 笔</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden flex">
                <div
                  className="h-full bg-emerald-500 rounded-l-full transition-all"
                  style={{ width: `${performance.win_rate}%` }}
                />
                <div
                  className="h-full bg-rose-500 rounded-r-full transition-all"
                  style={{ width: `${100 - performance.win_rate}%` }}
                />
              </div>
            </div>
          )}

          {/* 该股票最近信号列表 */}
          {signals.length > 0 ? (
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-2">{ticker} 近期信号</p>
              <div className="divide-y divide-slate-50 dark:divide-slate-800">
                {signals.map((sig) => (
                  <div key={sig.id} className="flex items-center gap-3 py-2">
                    {/* 信号类型标签 */}
                    <span className={clsx(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded",
                      sig.signal_type === "BUY" ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-600" :
                      sig.signal_type === "SELL" ? "bg-rose-50 dark:bg-rose-950 text-rose-600" :
                      "bg-slate-100 dark:bg-slate-800 text-slate-500"
                    )}>
                      {SIGNAL_TYPE_LABEL[sig.signal_type] || sig.signal_type}
                    </span>

                    {/* 入场价 */}
                    <span className="text-xs text-slate-600 dark:text-slate-300 tabular-nums">
                      @{Number(sig.entry_price).toFixed(2)}
                    </span>

                    {/* 状态 */}
                    <span className={clsx(
                      "text-[10px] ml-auto",
                      sig.signal_status === "ACTIVE" ? "text-blue-500" :
                      sig.pnl_percent != null && sig.pnl_percent > 0 ? "text-emerald-500" :
                      sig.pnl_percent != null && sig.pnl_percent < 0 ? "text-rose-500" :
                      "text-slate-400"
                    )}>
                      {sig.signal_status === "ACTIVE"
                        ? SIGNAL_STATUS_LABEL.ACTIVE
                        : sig.pnl_percent != null
                          ? `${sig.pnl_percent >= 0 ? "+" : ""}${Number(sig.pnl_percent).toFixed(1)}%`
                          : SIGNAL_STATUS_LABEL[sig.signal_status]}
                    </span>

                    {/* 日期 */}
                    <span className="text-[10px] text-slate-400 tabular-nums">{formatDate(sig.created_at)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 text-center py-2">该股票暂无信号记录</p>
          )}
        </div>
      )}
    </section>
  );
}

function StatCell({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "emerald" | "rose" | "slate";
}) {
  return (
    <div className="rounded-xl bg-slate-50 dark:bg-zinc-800 px-3 py-3 text-center">
      <p className={clsx(
        "text-lg font-black tabular-nums",
        color === "emerald" ? "text-emerald-600" :
        color === "rose" ? "text-rose-500" :
        "text-slate-700 dark:text-slate-200"
      )}>
        {value}
      </p>
      <p className="text-[10px] text-slate-400 mt-0.5">{label}</p>
    </div>
  );
}
