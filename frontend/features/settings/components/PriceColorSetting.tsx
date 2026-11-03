"use client";

import { useState } from "react";
import clsx from "clsx";
import { Check } from "lucide-react";
import { updateSettings } from "@/features/user/api";
import { applyPriceColorMode, priceHex, usePriceColorMode, type PriceColorMode } from "@/shared/theme/priceColor";

const OPTIONS: { key: PriceColorMode; label: string; desc: string }[] = [
  { key: "green_up", label: "绿涨红跌", desc: "国际惯例（默认）" },
  { key: "red_up", label: "红涨绿跌", desc: "A 股 / 港股习惯" },
];

const ROWS = [
  { t: "NVDA", n: "NVIDIA", p: "207.60", c: 1.15 },
  { t: "0700.HK", n: "腾讯控股", p: "392.20", c: 2.24 },
  { t: "AAPL", n: "Apple", p: "341.26", c: -1.11 },
];

function MiniCandles({ mode }: { mode: PriceColorMode }) {
  const c = priceHex(mode);
  const bars = [[30, 18, 1], [26, 14, -1], [34, 20, 1], [22, 12, -1], [38, 22, 1], [42, 16, 1], [30, 14, -1]] as const;
  return (
    <svg viewBox="0 0 112 56" className="h-14 w-28" aria-hidden>
      {bars.map(([y, h, d], i) => (
        <g key={i} fill={d > 0 ? c.up : c.down} stroke={d > 0 ? c.up : c.down}>
          <line x1={8 + i * 16} x2={8 + i * 16} y1={56 - y - 6} y2={56 - y + h + 4} strokeWidth={1} />
          <rect x={4 + i * 16} y={56 - y} width={8} height={h} rx={1} />
        </g>
      ))}
    </svg>
  );
}

/** 设置 → 外观：涨跌配色，带实时预览。立即生效并缓存到本地，同时同步到账号。 */
export function PriceColorSetting() {
  const mode = usePriceColorMode();
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const pick = async (m: PriceColorMode) => {
    if (m === mode) return;
    const prev = mode;
    applyPriceColorMode(m);
    setState("saving");
    try {
      await updateSettings({ price_color_mode: m });
      setState("saved");
    } catch {
      applyPriceColorMode(prev);
      setState("error");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">涨跌配色</p>
        <span className="text-xs text-neutral-500 dark:text-neutral-400">{state === "saving" ? "保存中…" : state === "saved" ? "已同步到账号" : state === "error" ? "保存失败，已恢复" : "全站立即生效：行情、K 线、持仓、简报、复盘"}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {OPTIONS.map((o) => {
          const c = priceHex(o.key);
          const active = mode === o.key;
          return (
            <button key={o.key} type="button" onClick={() => pick(o.key)} aria-pressed={active}
              className={clsx("rounded-2xl border p-4 text-left transition", active ? "border-neutral-900 bg-white ring-1 ring-neutral-900 dark:border-neutral-100 dark:bg-neutral-950 dark:ring-neutral-100" : "border-neutral-200 bg-white hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-950 dark:hover:border-neutral-700")}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{o.label}</p>
                  <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{o.desc}</p>
                </div>
                <span className={clsx("flex h-5 w-5 items-center justify-center rounded-full border", active ? "border-neutral-900 bg-neutral-900 text-white dark:border-neutral-100 dark:bg-neutral-100 dark:text-neutral-950" : "border-neutral-300 dark:border-neutral-700")}>{active && <Check className="h-3 w-3" />}</span>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="rounded-md px-2 py-0.5 text-[12px] font-medium" style={{ color: c.up, background: `${c.up}1a` }}>涨 +2.24%</span>
                <span className="rounded-md px-2 py-0.5 text-[12px] font-medium" style={{ color: c.down, background: `${c.down}1a` }}>跌 -1.11%</span>
              </div>
            </button>
          );
        })}
      </div>
      <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4 sm:flex-row sm:items-center dark:border-neutral-800 dark:bg-neutral-900/60">
        <div className="shrink-0"><p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-neutral-400">实时预览</p><MiniCandles mode={mode} /></div>
        <div className="min-w-0 flex-1 divide-y divide-neutral-200 dark:divide-neutral-800">
          {ROWS.map((r) => (
            <div key={r.t} className="flex items-center justify-between py-1.5 text-[13px]">
              <span><span className="font-bold text-neutral-900 dark:text-neutral-100">{r.t}</span> <span className="text-xs text-neutral-500">{r.n}</span></span>
              <span className="flex items-center gap-3">
                <span className={clsx("tabular-nums", r.c >= 0 ? "text-emerald-600" : "text-rose-600")}>{r.p}</span>
                <span className={clsx("tabular-nums w-16 rounded-md px-1.5 py-0.5 text-center text-xs font-bold", r.c >= 0 ? "bg-emerald-600/10 text-emerald-600" : "bg-rose-600/10 text-rose-600")}>{r.c >= 0 ? "+" : ""}{r.c.toFixed(2)}%</span>
              </span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11px] text-neutral-400">示例数据，仅用于预览配色。</p>
    </div>
  );
}
