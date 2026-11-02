"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { CheckCircle2, Clock3, MinusCircle, XCircle } from "lucide-react";
import { AgentPageShell } from "@/features/agent/components/AgentPageShell";
import { listAdvice, type AdviceRecord, type AdviceStats } from "@/features/agent/api";

const DIR: Record<string, { label: string; cls: string }> = {
  BUY: { label: "买入", cls: "bg-up-soft text-up" },
  SELL: { label: "卖出", cls: "bg-down-soft text-down" },
  HOLD: { label: "持有", cls: "bg-elevated text-ink-2" },
};
const SRC: Record<string, string> = { agent: "对话", diagnosis: "诊断", brief: "简报" };
const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "--" : `${v >= 0 ? "+" : ""}${v.toFixed(d)}%`);

function Stat({ label, value, sub, children, loading }: { label: string; value: string; sub?: string; children?: React.ReactNode; loading?: boolean }) {
  return (
    <div className="card p-5">
      <p className="eyebrow">{label}</p>
      {loading ? <div className="skeleton mt-3 h-8 w-20 rounded-md" /> : <p className="num mt-2 text-[28px] font-semibold leading-none tracking-tight text-ink">{value}</p>}
      {children}
      {sub && <p className="mt-2 text-[12px] text-ink-3">{sub}</p>}
    </div>
  );
}

function Result({ r }: { r: AdviceRecord }) {
  if (r.status === "open") return <span className="inline-flex items-center gap-1 text-ink-3"><Clock3 className="h-3.5 w-3.5" />{r.due_at.slice(5, 10)} 到期</span>;
  if (r.status === "error") return <span className="inline-flex items-center gap-1 text-ink-3"><MinusCircle className="h-3.5 w-3.5" />无法复盘</span>;
  return r.hit
    ? <span className="inline-flex items-center gap-1 font-medium text-brand"><CheckCircle2 className="h-3.5 w-3.5" />命中</span>
    : <span className="inline-flex items-center gap-1 text-ink-3"><XCircle className="h-3.5 w-3.5" />未中</span>;
}

export default function ReviewPage() {
  const [items, setItems] = useState<AdviceRecord[]>([]);
  const [stats, setStats] = useState<AdviceStats | null>(null);
  const [disclaimer, setDisclaimer] = useState("");
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "open" | "evaluated">("all");

  useEffect(() => {
    listAdvice().then((r) => { setItems(r.items); setStats(r.stats); setDisclaimer(r.disclaimer); }).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  const shown = items.filter((i) => filter === "all" || i.status === filter);
  const hitRate = stats?.hit_rate == null ? null : stats.hit_rate * 100;

  return (
    <AgentPageShell>
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">复盘战绩</h1>
          <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-ink-3">智能体在对话、个股诊断和每日简报中给出的买入 / 卖出 / 持有建议会自动入档，到期后按收盘价复盘。判定规则：买入 → 期间上涨算命中；卖出 → 期间下跌算命中；持有 → 跌幅不超过 5% 算命中。</p>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="命中率" loading={loading} value={hitRate == null ? "--" : `${hitRate.toFixed(0)}%`} sub={`${stats?.hits ?? 0} / ${stats?.evaluated ?? 0} 条已复盘`}>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-elevated"><div className="h-full rounded-full bg-brand" style={{ width: `${hitRate ?? 0}%` }} /></div>
          </Stat>
          <Stat label="方向收益均值" loading={loading} value={pct(stats?.avg_directional_return_pct)} sub="卖出建议按反向计" />
          <Stat label="累计建议" loading={loading} value={String(stats?.total ?? 0)} sub="对话 · 诊断 · 简报" />
          <Stat label="待复盘" loading={loading} value={String(stats?.open ?? 0)} sub="到期后自动评估" />
        </div>

        <div className="card overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <p className="text-[14px] font-semibold text-ink">建议档案</p>
            <div className="flex rounded-lg bg-elevated p-0.5 text-[12.5px]">
              {([["all", "全部"], ["open", "待复盘"], ["evaluated", "已复盘"]] as const).map(([k, l]) => (
                <button key={k} type="button" onClick={() => setFilter(k)} className={clsx("rounded-md px-3 py-1 transition", filter === k ? "bg-surface font-medium text-ink shadow-sm" : "text-ink-3 hover:text-ink")}>{l}</button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-[13px]">
              <thead className="bg-canvas/60 text-left text-[11.5px] text-ink-3">
                <tr>{["日期", "股票", "建议", "周期", "建议时价", "复盘价", "期间涨跌", "结果", "来源 / 理由"].map((h, i) => <th key={h} className={clsx("px-4 py-2.5 font-medium", i >= 4 && i <= 6 && "text-right")}>{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-line">
                {loading && [0, 1, 2].map((i) => <tr key={i}><td colSpan={9} className="px-4 py-3"><div className="skeleton h-4 w-full rounded" /></td></tr>)}
                {!loading && shown.map((r) => (
                  <tr key={r.id} className="transition hover:bg-canvas/60">
                    <td className="num whitespace-nowrap px-4 py-3 text-ink-3">{r.created_at.slice(0, 10)}</td>
                    <td className="px-4 py-3 font-semibold text-ink">{r.ticker}</td>
                    <td className="px-4 py-3"><span className={clsx("rounded-md px-2 py-0.5 text-[12px] font-medium", DIR[r.direction]?.cls)}>{DIR[r.direction]?.label ?? r.direction}</span></td>
                    <td className="num px-4 py-3 text-ink-2">{r.horizon_days} 天</td>
                    <td className="num px-4 py-3 text-right text-ink-2">{r.price_at?.toFixed(2) ?? "--"}</td>
                    <td className="num px-4 py-3 text-right text-ink-2">{r.eval_price?.toFixed(2) ?? "--"}</td>
                    <td className={clsx("num px-4 py-3 text-right font-medium", r.return_pct == null ? "text-ink-3" : r.return_pct >= 0 ? "text-up" : "text-down")}>{pct(r.return_pct, 2)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-[12.5px]"><Result r={r} /></td>
                    <td className="max-w-xs truncate px-4 py-3 text-[12.5px] text-ink-3" title={r.rationale || ""}><span className="mr-1.5 rounded bg-elevated px-1.5 py-0.5 text-[11px] text-ink-2">{SRC[r.source] ?? r.source}</span>{r.rationale}</td>
                  </tr>
                ))}
                {!loading && shown.length === 0 && <tr><td colSpan={9} className="px-4 py-14 text-center text-[13px] text-ink-3">暂无记录。去和智能体聊聊你的持仓，它给出的建议会出现在这里。</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <p className="text-[11.5px] text-ink-3">{disclaimer} 历史命中率不代表未来表现。</p>
      </div>
    </AgentPageShell>
  );
}
