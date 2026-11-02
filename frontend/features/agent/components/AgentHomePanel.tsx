"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { ArrowUpRight, Loader2, Newspaper, PieChart, RefreshCw, Trophy } from "lucide-react";
import type { PortfolioItem } from "@/types";
import { generateBrief, listAdvice, listBriefs, type AdviceStats, type DailyBrief } from "@/features/agent/api";

type Row = PortfolioItem & { change_percent?: number | null };

export function ChangePill({ value, className }: { value: number | null | undefined; className?: string }) {
  if (value === null || value === undefined) return <span className={clsx("num text-[12px] text-ink-3", className)}>--</span>;
  return (
    <span className={clsx("num inline-flex min-w-[62px] justify-end rounded-md px-1.5 py-0.5 text-[12px] font-medium", value > 0 ? "bg-up-soft text-up" : value < 0 ? "bg-down-soft text-down" : "bg-elevated text-ink-3", className)}>
      {value > 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

function CardHead({ icon, title, action }: { icon: React.ReactNode; title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 pb-2 pt-3.5">
      <h2 className="flex items-center gap-2 text-[13px] font-semibold text-ink"><span className="text-ink-3">{icon}</span>{title}</h2>
      <div className="flex items-center gap-3 text-[12px]">{action}</div>
    </div>
  );
}

/** 智能体首页：今日简报 + 持仓/自选异动 + 战绩概览。variant="rail" 为右栏（xl+），"inline" 用于窄屏时嵌在对话空状态下。 */
export function AgentHomePanel({ portfolio, onAsk, variant = "rail" }: { portfolio: PortfolioItem[]; onAsk: (q: string) => void; variant?: "rail" | "inline" }) {
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<AdviceStats | null | undefined>(undefined);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    listBriefs(1).then((r) => setBrief(r.items[0] || null)).catch(() => undefined).finally(() => setLoadingBrief(false));
    listAdvice().then((r) => setStats(r.stats)).catch(() => setStats(null));
  }, []);

  const gen = async () => {
    setGenerating(true);
    setErr(null);
    try {
      setBrief(await generateBrief(false));
    } catch (e: unknown) {
      setErr((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "生成失败，请稍后重试");
    } finally {
      setGenerating(false);
    }
  };

  const rows = [...(portfolio as Row[])].sort((a, b) => Math.abs(b.change_percent ?? 0) - Math.abs(a.change_percent ?? 0));
  const holds = rows.filter((r) => (r.quantity ?? 0) > 0);
  const watch = rows.filter((r) => !(r.quantity ?? 0));
  const hitPct = stats?.hit_rate == null ? null : Math.round(stats.hit_rate * 100);

  return (
    <aside className={clsx(variant === "rail" ? "hidden w-[360px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-line bg-canvas p-3 xl:flex 2xl:w-[400px] [&>*]:shrink-0" : "grid gap-3 md:grid-cols-2")}>
      {/* 今日简报 */}
      <section className={clsx("card overflow-hidden", variant === "inline" && "md:col-span-2")}>
        <CardHead
          icon={<Newspaper className="h-4 w-4" />}
          title="今日简报"
          action={
            <>
              <button type="button" onClick={gen} disabled={generating} className="inline-flex items-center gap-1 text-ink-3 hover:text-ink disabled:opacity-50">
                {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}{brief ? "重新生成" : "生成"}
              </button>
              <Link href="/briefs" className="inline-flex items-center text-ink-3 hover:text-ink">全部<ArrowUpRight className="h-3 w-3" /></Link>
            </>
          }
        />
        <div className="px-4 pb-4">
          {loadingBrief || generating ? (
            <div className="space-y-2 pt-1">
              {generating && <p className="text-[12px] text-ink-3">智能体正在梳理你的持仓与新闻，约需 30–60 秒…</p>}
              <div className="skeleton h-3.5 w-2/3" /><div className="skeleton h-3 w-full" /><div className="skeleton h-3 w-11/12" /><div className="skeleton h-3 w-4/5" />
            </div>
          ) : brief ? (
            <>
              <div className="mb-2 flex items-center gap-2">
                <span className="num rounded-md bg-elevated px-1.5 py-0.5 text-[11px] text-ink-3">{brief.date}</span>
                {brief.pushed_channels && <span className="text-[11px] text-ink-3">已推送 · {brief.pushed_channels}</span>}
              </div>
              <div className={clsx("relative", !expanded && "max-h-64 overflow-hidden")}>
                <div className="prose-agent text-[13px] [&_h1]:text-[14px] [&_h2]:text-[13.5px] [&_h2]:mt-3 [&_h1]:mt-0 [&_h2:first-child]:mt-0">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{brief.content}</ReactMarkdown>
                </div>
                {!expanded && <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-surface to-transparent" />}
              </div>
              <button type="button" onClick={() => setExpanded((v) => !v)} className="mt-2 text-[12px] font-medium text-brand hover:underline">{expanded ? "收起" : "展开全文"}</button>
            </>
          ) : (
            <div className="rounded-lg border border-dashed border-line-strong p-4 text-center">
              <p className="text-[13px] font-medium text-ink">还没有今天的简报</p>
              <p className="mt-1 text-[12px] leading-relaxed text-ink-3">智能体会结合持仓、自选与投资画像写一份盘前简报，也可在设置里配置每日推送。</p>
              <button type="button" onClick={gen} className="mt-3 inline-flex h-8 items-center rounded-lg bg-ink px-3 text-[12.5px] font-medium text-canvas">生成今日简报</button>
            </div>
          )}
          {err && <p className="mt-2 text-[12px] text-down">{err}</p>}
        </div>
      </section>

      {/* 持仓与自选异动 */}
      <section className="card">
        <CardHead icon={<PieChart className="h-4 w-4" />} title="持仓与自选异动" action={<Link href="/dashboard?tab=portfolio" className="inline-flex items-center text-ink-3 hover:text-ink">管理<ArrowUpRight className="h-3 w-3" /></Link>} />
        <div className="px-2 pb-3">
          {rows.length === 0 ? (
            <div className="mx-2 rounded-lg border border-dashed border-line-strong p-4 text-center text-[12px] text-ink-3">
              还没有持仓或自选。<Link href="/dashboard?tab=portfolio" className="font-medium text-brand">去添加</Link>，智能体就能帮你盯盘。
            </div>
          ) : (
            [{ label: "持仓", list: holds }, { label: "自选", list: watch }].filter((g) => g.list.length).map((g) => (
              <div key={g.label} className="mb-1">
                <p className="eyebrow px-2 pb-1 pt-1.5">{g.label} · {g.list.length}</p>
                <ul>
                  {g.list.slice(0, 6).map((r) => {
                    const c = r.change_percent ?? null;
                    return (
                      <li key={r.ticker}>
                        <button type="button" title="让智能体解释今天的异动" onClick={() => onAsk(`${r.ticker} 今天为什么${c !== null && c < 0 ? "跌" : "涨"}？结合我的持仓给点建议`)} className="group flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left hover:bg-elevated">
                          <span className="min-w-0 flex-1">
                            <span className="block text-[13px] font-medium text-ink">{r.ticker}</span>
                            <span className="block truncate text-[11px] text-ink-3">{r.name && r.name !== r.ticker ? r.name : "—"}</span>
                          </span>
                          <span className="num text-right text-[12.5px] text-ink-2">{r.current_price ? r.current_price.toFixed(2) : "--"}</span>
                          <ChangePill value={c} />
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 战绩 */}
      <Link href="/review" className="card group block p-4 transition-colors hover:border-line-strong">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-[13px] font-semibold text-ink"><Trophy className="h-4 w-4 text-ink-3" />复盘战绩</h2>
          <ArrowUpRight className="h-3.5 w-3.5 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </div>
        {stats === undefined ? (
          <div className="mt-3 space-y-2"><div className="skeleton h-7 w-20" /><div className="skeleton h-3 w-40" /></div>
        ) : stats && stats.total > 0 ? (
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="num text-[28px] font-semibold leading-none tracking-tight text-ink">{hitPct === null ? "--" : `${hitPct}%`}</span>
              <span className="text-[12px] text-ink-3">命中率</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-elevated">
              <div className="h-full rounded-full bg-brand" style={{ width: `${hitPct ?? 0}%` }} />
            </div>
            <p className="num mt-2 text-[12px] text-ink-3">累计 {stats.total} 条 · 已复盘 {stats.evaluated} · 待复盘 {stats.open}</p>
          </div>
        ) : (
          <p className="mt-2 text-[12px] leading-relaxed text-ink-3">智能体给出的每条买入 / 卖出 / 持有建议都会被记录，到期按真实行情自动复盘。</p>
        )}
      </Link>
    </aside>
  );
}
