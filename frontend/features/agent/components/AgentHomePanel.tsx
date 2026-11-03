"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { Loader2, Newspaper, PieChart, RefreshCw, Trophy } from "lucide-react";
import type { PortfolioItem } from "@/types";
import { generateBrief, listAdvice, listBriefs, type AdviceStats, type DailyBrief } from "@/features/agent/api";

type Row = PortfolioItem & { change_percent?: number | null };

/** 智能体首页右栏：今日简报 + 持仓/自选今日异动 + 战绩概览。 */
export function AgentHomePanel({ portfolio, onAsk }: { portfolio: PortfolioItem[]; onAsk: (q: string) => void }) {
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [stats, setStats] = useState<AdviceStats | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    listBriefs(1).then((r) => setBrief(r.items[0] || null)).catch(() => undefined).finally(() => setLoadingBrief(false));
    listAdvice().then((r) => setStats(r.stats)).catch(() => undefined);
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

  return (
    <aside className="hidden xl:flex w-96 shrink-0 flex-col gap-4 overflow-y-auto border-l border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 p-4">
      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900 dark:text-neutral-100"><Newspaper className="h-4 w-4 text-blue-600" /> 今日简报</h2>
          <div className="flex items-center gap-2 text-xs">
            <button type="button" onClick={gen} disabled={generating} className="flex items-center gap-1 text-blue-600 disabled:opacity-50">
              {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />} {brief ? "重新生成" : "生成"}
            </button>
            <Link href="/briefs" className="text-neutral-500 hover:text-neutral-800">全部</Link>
          </div>
        </div>
        {loadingBrief ? (
          <p className="text-xs text-neutral-400">加载中…</p>
        ) : brief ? (
          <div>
            <p className="mb-1 text-xs text-neutral-400">{brief.date} · {brief.title}</p>
            <div className={clsx("prose prose-xs dark:prose-invert max-w-none text-[13px] leading-relaxed text-neutral-700 dark:text-neutral-300", !expanded && "max-h-72 overflow-hidden")}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{brief.content}</ReactMarkdown>
            </div>
            <button type="button" onClick={() => setExpanded((v) => !v)} className="mt-1 text-xs text-blue-600">{expanded ? "收起" : "展开全文"}</button>
          </div>
        ) : (
          <p className="text-xs leading-relaxed text-neutral-500">还没有今天的简报。点击「生成」，智能体会结合你的持仓、自选与投资画像写一份盘前简报；也可以在 设置 → 推送渠道 里配置钉钉/Webhook，每天定时推送。</p>
        )}
        {err && <p className="mt-2 text-xs text-rose-600">{err}</p>}
      </div>

      <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900 dark:text-neutral-100"><PieChart className="h-4 w-4 text-blue-600" /> 持仓与自选异动</h2>
          <Link href="/dashboard?tab=portfolio" className="text-xs text-neutral-500 hover:text-neutral-800">管理</Link>
        </div>
        {rows.length === 0 ? (
          <p className="text-xs text-neutral-500">还没有持仓或自选。去 <Link href="/dashboard?tab=portfolio" className="text-blue-600">持仓与自选</Link> 添加几只股票，智能体就能主动盯盘。</p>
        ) : (
          <div className="space-y-3">
            {[{ label: "持仓", list: holds }, { label: "自选", list: watch }].filter((g) => g.list.length).map((g) => (
              <div key={g.label}>
                <p className="mb-1 text-[11px] text-neutral-400">{g.label}</p>
                <ul className="space-y-1">
                  {g.list.slice(0, 8).map((r) => {
                    const c = r.change_percent ?? null;
                    return (
                      <li key={r.ticker}>
                        <button type="button" onClick={() => onAsk(`${r.ticker} 今天为什么${c !== null && c < 0 ? "跌" : "涨"}？结合我的持仓给点建议`)} className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800">
                          <span className="truncate text-neutral-800 dark:text-neutral-200"><span className="font-medium">{r.ticker}</span> <span className="text-xs text-neutral-400">{r.name && r.name !== r.ticker ? r.name : ""}</span></span>
                          <span className={clsx("tabular-nums text-xs font-medium", c === null ? "text-neutral-400" : c >= 0 ? "text-emerald-600" : "text-rose-600")}>{c === null ? "--" : `${c >= 0 ? "+" : ""}${c.toFixed(2)}%`}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
            <p className="text-[11px] text-neutral-400">点击任一股票，让智能体解释异动。</p>
          </div>
        )}
      </div>

      <Link href="/review" className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-4 hover:border-blue-300">
        <h2 className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-neutral-900 dark:text-neutral-100"><Trophy className="h-4 w-4 text-amber-500" /> 复盘战绩</h2>
        {stats && stats.total > 0 ? (
          <p className="text-xs text-neutral-500">累计 {stats.total} 条建议 · 已复盘 {stats.evaluated} 条 · 命中率 <span className="font-semibold text-neutral-900 dark:text-neutral-100">{stats.hit_rate === null ? "--" : `${(stats.hit_rate * 100).toFixed(0)}%`}</span></p>
        ) : (
          <p className="text-xs text-neutral-500">智能体给出的每条买/卖/持有建议都会被记录，到期自动复盘。</p>
        )}
      </Link>
    </aside>
  );
}
