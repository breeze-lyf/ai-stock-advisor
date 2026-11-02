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
        <p className="text-sm font-semibold text-ink">涨跌配色</p>
        <span className="text-[12px] text-ink-3">{state === "saving" ? "保存中…" : state === "saved" ? "已同步到账号" : state === "error" ? "保存失败，已恢复" : "全站立即生效：行情、K 线、持仓、简报、复盘"}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {OPTIONS.map((o) => {
          const c = priceHex(o.key);
          const active = mode === o.key;
          return (
            <button key={o.key} type="button" onClick={() => pick(o.key)} aria-pressed={active}
              className={clsx("rounded-2xl border p-4 text-left transition", active ? "border-ink bg-surface shadow-card ring-1 ring-ink" : "border-line bg-surface hover:border-line-strong")}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[14px] font-semibold text-ink">{o.label}</p>
                  <p className="mt-0.5 text-[12px] text-ink-3">{o.desc}</p>
                </div>
                <span className={clsx("flex h-5 w-5 items-center justify-center rounded-full border", active ? "border-ink bg-ink text-canvas" : "border-line-strong")}>{active && <Check className="h-3 w-3" />}</span>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="rounded-md px-2 py-0.5 text-[12px] font-medium" style={{ color: c.up, background: `${c.up}1a` }}>涨 +2.24%</span>
                <span className="rounded-md px-2 py-0.5 text-[12px] font-medium" style={{ color: c.down, background: `${c.down}1a` }}>跌 -1.11%</span>
              </div>
            </button>
          );
        })}
      </div>
      <div className="card flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
        <div className="shrink-0"><p className="eyebrow mb-1">实时预览</p><MiniCandles mode={mode} /></div>
        <div className="min-w-0 flex-1 divide-y divide-line">
          {ROWS.map((r) => (
            <div key={r.t} className="flex items-center justify-between py-1.5 text-[13px]">
              <span><span className="font-semibold text-ink">{r.t}</span> <span className="text-ink-3">{r.n}</span></span>
              <span className="flex items-center gap-3">
                <span className={clsx("num", r.c >= 0 ? "text-up" : "text-down")}>{r.p}</span>
                <span className={clsx("num w-16 rounded-md px-1.5 py-0.5 text-center text-[12px] font-medium", r.c >= 0 ? "bg-up-soft text-up" : "bg-down-soft text-down")}>{r.c >= 0 ? "+" : ""}{r.c.toFixed(2)}%</span>
              </span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11.5px] text-ink-3">示例数据，仅用于预览配色。</p>
    </div>
  );
}
