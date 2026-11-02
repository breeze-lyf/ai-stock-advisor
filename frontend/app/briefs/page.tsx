"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { Loader2, Newspaper, Send, Sparkles } from "lucide-react";
import { AgentPageShell } from "@/features/agent/components/AgentPageShell";
import { generateBrief, listBriefs, type BriefList, type DailyBrief } from "@/features/agent/api";

export default function BriefsPage() {
  const [data, setData] = useState<BriefList | null>(null);
  const [sel, setSel] = useState<DailyBrief | null>(null);
  const [busy, setBusy] = useState<"gen" | "push" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => listBriefs(30).then((d) => { setData(d); setSel((s) => s ?? d.items[0] ?? null); }).catch(() => setMsg("加载失败"));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const gen = async (push: boolean) => {
    setBusy(push ? "push" : "gen");
    setMsg(null);
    try {
      const b = await generateBrief(push);
      setSel(b);
      setMsg(push ? (b.pushed_channels ? `已推送：${b.pushed_channels}` : "已生成，但没有可用的推送渠道（去 设置 → 推送渠道 配置）") : "已生成今日简报");
      load();
    } catch (e: unknown) {
      setMsg((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "生成失败");
    } finally {
      setBusy(null);
    }
  };

  return (
    <AgentPageShell>
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold tracking-tight text-ink">每日简报</h1>
            <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-ink-3">
              {data?.scheduled ? `定时简报已开启：每天 ${data.hour}:00（北京时间）自动生成并推送。` : "定时简报未在服务端开启（AGENT_BRIEF_ENABLED），可随时手动生成。"}
              {" "}推送渠道在 <Link href="/settings?section=push" className="text-brand hover:underline">设置 → 推送渠道</Link> 配置。
            </p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => gen(true)} disabled={!!busy} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-line bg-surface px-3.5 text-[13px] font-medium text-ink-2 hover:text-ink disabled:opacity-50">{busy === "push" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} 生成并推送</button>
            <button type="button" onClick={() => gen(false)} disabled={!!busy} className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-ink px-3.5 text-[13px] font-medium text-canvas hover:opacity-90 disabled:opacity-50">{busy === "gen" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} 生成今日简报</button>
          </div>
        </div>
        {msg && <p className="mb-4 rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink-2">{msg}</p>}
        <div className="flex flex-col gap-6 md:flex-row">
          <aside className="md:w-56 md:shrink-0">
            <p className="eyebrow mb-2 px-1">历史简报</p>
            <div className="flex gap-1.5 overflow-x-auto md:flex-col md:overflow-visible">
              {!data && [0, 1, 2].map((i) => <div key={i} className="skeleton h-12 w-full rounded-lg" />)}
              {data?.items.map((b) => (
                <button key={b.id} type="button" onClick={() => setSel(b)} className={clsx("min-w-[150px] rounded-lg px-3 py-2 text-left transition md:min-w-0", sel?.id === b.id ? "bg-surface shadow-card ring-1 ring-line" : "hover:bg-elevated")}>
                  <div className="num text-[13px] font-medium text-ink">{b.date}</div>
                  <div className="truncate text-[12px] text-ink-3">{b.status === "error" ? "生成失败" : b.title}</div>
                </button>
              ))}
              {data && data.items.length === 0 && <p className="px-1 text-[12px] text-ink-3">暂无简报</p>}
            </div>
          </aside>
          <section className="min-w-0 flex-1">
            {sel ? (
              <article className="card p-6 sm:p-8">
                <div className="mb-5 flex flex-wrap items-center gap-2 border-b border-line pb-4">
                  <Newspaper className="h-4 w-4 text-brand" />
                  <span className="num text-[13px] font-medium text-ink">{sel.date}</span>
                  {sel.tickers.map((t) => <span key={t} className="rounded-md bg-elevated px-1.5 py-0.5 text-[11.5px] text-ink-2">{t}</span>)}
                  {sel.pushed_channels && <span className="ml-auto text-[12px] text-ink-3">已推送 {sel.pushed_channels}</span>}
                </div>
                <div className="prose-agent prose prose-sm max-w-none dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm]}>{sel.content}</ReactMarkdown></div>
                <p className="mt-6 border-t border-line pt-4 text-[11.5px] text-ink-3">{data?.disclaimer}</p>
              </article>
            ) : data ? (
              <div className="rounded-2xl border border-dashed border-line-strong p-12 text-center text-[13px] text-ink-3">还没有简报。先在 <Link href="/dashboard?tab=portfolio" className="text-brand">持仓与自选</Link> 添加股票，再点击「生成今日简报」。</div>
            ) : (
              <div className="card space-y-3 p-8">{[80, 95, 60, 90, 70].map((w, i) => <div key={i} className="skeleton h-4 rounded" style={{ width: `${w}%` }} />)}</div>
            )}
          </section>
        </div>
      </div>
    </AgentPageShell>
  );
}
