"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { Trophy } from "lucide-react";
import { AgentPageShell } from "@/features/agent/components/AgentPageShell";
import { listAdvice, type AdviceRecord, type AdviceStats } from "@/features/agent/api";

const DIR: Record<string, { label: string; cls: string }> = {
  BUY: { label: "买入", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" },
  SELL: { label: "卖出", cls: "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300" },
  HOLD: { label: "持有", cls: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300" },
};
const SRC: Record<string, string> = { agent: "对话", diagnosis: "诊断", brief: "简报" };
const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "--" : `${v >= 0 ? "+" : ""}${v.toFixed(d)}%`);

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-black tabular-nums text-neutral-900 dark:text-neutral-100">{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-neutral-400">{sub}</p>}
    </div>
  );
}

export default function ReviewPage() {
  const [items, setItems] = useState<AdviceRecord[]>([]);
  const [stats, setStats] = useState<AdviceStats | null>(null);
  const [disclaimer, setDisclaimer] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "evaluated">("all");

  useEffect(() => {
    listAdvice().then((r) => { setItems(r.items); setStats(r.stats); setDisclaimer(r.disclaimer); }).catch(() => undefined);
  }, []);

  const shown = items.filter((i) => filter === "all" || i.status === filter);

  return (
    <AgentPageShell>
      <div className="mx-auto max-w-6xl space-y-5 px-4 py-6">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-bold text-neutral-900 dark:text-neutral-100"><Trophy className="h-5 w-5 text-amber-500" /> 复盘战绩</h1>
          <p className="mt-1 text-xs text-neutral-500">智能体在对话、个股诊断和每日简报中给出的买入/卖出/持有建议会自动入档，到期后按收盘价复盘。判定规则：买入→期间上涨算命中；卖出→期间下跌算命中；持有→跌幅不超过 5% 算命中。</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="命中率" value={stats?.hit_rate == null ? "--" : `${(stats.hit_rate * 100).toFixed(0)}%`} sub={`${stats?.hits ?? 0} / ${stats?.evaluated ?? 0} 条已复盘`} />
          <Stat label="方向收益均值" value={pct(stats?.avg_directional_return_pct)} sub="卖出建议按反向计" />
          <Stat label="累计建议" value={String(stats?.total ?? 0)} />
          <Stat label="待复盘" value={String(stats?.open ?? 0)} />
        </div>
        <div className="flex gap-2 text-sm">
          {([["all", "全部"], ["open", "待复盘"], ["evaluated", "已复盘"]] as const).map(([k, l]) => (
            <button key={k} type="button" onClick={() => setFilter(k)} className={clsx("rounded-lg px-3 py-1", filter === k ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}>{l}</button>
          ))}
        </div>
        <div className="overflow-x-auto rounded-2xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 text-left text-xs text-neutral-500 dark:border-neutral-800">
              <tr>{["日期", "股票", "建议", "周期", "建议时价", "复盘价", "收益", "结果", "来源 / 理由"].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id} className="border-b border-neutral-100 last:border-0 dark:border-neutral-800">
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-neutral-500">{r.created_at.slice(0, 10)}</td>
                  <td className="px-3 py-2 font-medium">{r.ticker}</td>
                  <td className="px-3 py-2"><span className={clsx("rounded px-1.5 py-0.5 text-xs font-medium", DIR[r.direction]?.cls)}>{DIR[r.direction]?.label ?? r.direction}</span></td>
                  <td className="px-3 py-2 text-xs">{r.horizon_days} 天</td>
                  <td className="px-3 py-2 tabular-nums">{r.price_at?.toFixed(2) ?? "--"}</td>
                  <td className="px-3 py-2 tabular-nums">{r.eval_price?.toFixed(2) ?? "--"}</td>
                  <td className={clsx("px-3 py-2 tabular-nums", (r.return_pct ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600")}>{pct(r.return_pct, 2)}</td>
                  <td className="px-3 py-2 text-xs">{r.status === "open" ? <span className="text-neutral-400">{r.due_at.slice(0, 10)} 到期</span> : r.status === "error" ? <span className="text-neutral-400">无法复盘</span> : r.hit ? <span className="font-semibold text-blue-600 dark:text-blue-400">✓ 命中</span> : <span className="text-neutral-400">✗ 未中</span>}</td>
                  <td className="max-w-xs truncate px-3 py-2 text-xs text-neutral-500" title={r.rationale || ""}>[{SRC[r.source] ?? r.source}] {r.rationale}</td>
                </tr>
              ))}
              {shown.length === 0 && <tr><td colSpan={9} className="px-3 py-10 text-center text-sm text-neutral-500">暂无记录。去和智能体聊聊你的持仓，它给出的建议会出现在这里。</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-neutral-400">{disclaimer} 历史命中率不代表未来表现。</p>
      </div>
    </AgentPageShell>
  );
}
