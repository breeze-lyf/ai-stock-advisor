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
      <div className="mx-auto flex max-w-6xl gap-6 px-4 py-6">
        <aside className="w-56 shrink-0 space-y-1">
          <h1 className="mb-3 flex items-center gap-2 text-lg font-bold text-neutral-900 dark:text-neutral-100"><Newspaper className="h-5 w-5 text-blue-600" /> 每日简报</h1>
          {data?.items.map((b) => (
            <button key={b.id} type="button" onClick={() => setSel(b)} className={clsx("w-full rounded-lg px-3 py-2 text-left text-sm", sel?.id === b.id ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}>
              <div className="font-medium">{b.date}</div>
              <div className="truncate text-xs opacity-70">{b.status === "error" ? "生成失败" : b.title}</div>
            </button>
          ))}
          {data && data.items.length === 0 && <p className="text-xs text-neutral-500">暂无简报</p>}
        </aside>
        <section className="min-w-0 flex-1 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
            <p className="text-xs text-neutral-500">
              {data?.scheduled ? `定时简报已开启：每天 ${data.hour}:00（北京时间）自动生成并推送。` : "定时简报未在服务端开启（AGENT_BRIEF_ENABLED），可随时手动生成。"}
              {" "}推送渠道在 <Link href="/settings?section=push" className="text-blue-600">设置 → 推送渠道</Link> 配置。
            </p>
            <div className="flex gap-2">
              <button type="button" onClick={() => gen(false)} disabled={!!busy} className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">{busy === "gen" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} 生成今日简报</button>
              <button type="button" onClick={() => gen(true)} disabled={!!busy} className="flex items-center gap-1.5 rounded-lg border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 disabled:opacity-50">{busy === "push" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} 生成并推送</button>
            </div>
          </div>
          {msg && <p className="text-sm text-neutral-600 dark:text-neutral-300">{msg}</p>}
          {sel ? (
            <article className="rounded-2xl border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <p className="mb-3 text-xs text-neutral-400">{sel.date} · {sel.tickers.join(" / ")}{sel.pushed_channels ? ` · 已推送 ${sel.pushed_channels}` : ""}</p>
              <div className="prose prose-sm max-w-none dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm]}>{sel.content}</ReactMarkdown></div>
              <p className="mt-4 text-[11px] text-neutral-400">{data?.disclaimer}</p>
            </article>
          ) : (
            <div className="rounded-2xl border border-dashed border-neutral-300 p-10 text-center text-sm text-neutral-500 dark:border-neutral-700">还没有简报。先在 <Link href="/dashboard?tab=portfolio" className="text-blue-600">持仓与自选</Link> 添加股票，再点击「生成今日简报」。</div>
          )}
        </section>
      </div>
    </AgentPageShell>
  );
}
