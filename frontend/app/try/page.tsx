"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Loader2, Send, ShieldAlert } from "lucide-react";
import { getPublicConfig, sendTrialMessage, type AgentSource, type AgentStep } from "@/features/agent/api";
import { Sources, ToolSteps } from "@/features/agent/components/AgentWorkspace";
import { BRAND } from "@/shared/config/features";

const SUGGESTIONS = ["NVDA 现在的技术面怎么样？", "腾讯 0700.HK 估值贵不贵？", "最近有哪些宏观热点？", "贵州茅台 600519 近期新闻"];

interface Msg { role: "user" | "assistant"; content: string; steps?: AgentStep[]; sources?: AgentSource[] }

/** 免登录试用：按 IP 每日限额，仅开放只读行情/新闻/宏观工具，不访问任何账户数据，不保存对话。 */
export default function TryPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [enabled, setEnabled] = useState(true);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getPublicConfig().then((c) => { setEnabled(c.trial_enabled); setRemaining((r) => r ?? c.trial_daily_limit); }).catch(() => undefined);
  }, []);
  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [msgs, loading]);

  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setError(null);
    setMsgs((m) => [...m, { role: "user", content: q }]);
    setLoading(true);
    try {
      const r = await sendTrialMessage(q);
      setRemaining(r.remaining);
      setMsgs((m) => [...m, { role: "assistant", content: r.answer, steps: r.steps, sources: r.sources }]);
    } catch (e: unknown) {
      const res = (e as { response?: { status?: number; data?: { detail?: string } } })?.response;
      if (res?.status === 429) setRemaining(0);
      setError(res?.data?.detail || "请求失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-neutral-50 dark:bg-neutral-950">
      <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
        <Link href="/" className="flex items-center gap-2 font-bold"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white"><Bot className="h-4 w-4" /></span>{BRAND.name} · 试用</Link>
        <div className="flex items-center gap-3 text-sm">
          {remaining !== null && <span className="text-xs text-neutral-500">今日剩余 {remaining} 次</span>}
          <Link href="/register" className="rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white">注册解锁完整功能</Link>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
            试用模式：仅开放行情、技术面、基本面、新闻、宏观等只读工具；不读取任何账户/持仓数据，不保存对话。注册后智能体会记住你的持仓与投资画像，并提供每日简报和建议复盘。
          </div>
          {!enabled && <p className="text-sm text-rose-600">试用暂未开放，请注册后使用。</p>}
          {msgs.length === 0 && enabled && (
            <div className="grid gap-2 pt-6 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => send(s)} className="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-left text-sm hover:border-blue-300 dark:border-neutral-800 dark:bg-neutral-900">{s}</button>
              ))}
            </div>
          )}
          {msgs.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end"><div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2.5 text-sm text-white">{m.content}</div></div>
            ) : (
              <div key={i} className="rounded-2xl border border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
                {m.steps && <ToolSteps steps={m.steps} />}
                <div className="prose prose-sm max-w-none dark:prose-invert"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
                {m.sources && <Sources sources={m.sources} />}
              </div>
            ),
          )}
          {loading && <div className="flex items-center gap-2 text-sm text-neutral-500"><Loader2 className="h-4 w-4 animate-spin" /> 智能体正在查询数据…</div>}
          {error && <p className="text-sm text-rose-600">{error} {remaining === 0 && <Link href="/register" className="text-blue-600 underline">注册继续使用</Link>}</p>}
          <div ref={bottom} />
        </div>
      </div>
      <div className="border-t border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
        <form className="mx-auto flex max-w-3xl gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} disabled={!enabled || remaining === 0} placeholder={remaining === 0 ? "今日试用次数已用完，注册后可继续使用" : "问一只股票或一个市场话题…"} className="flex-1 rounded-xl border border-neutral-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-500 dark:border-neutral-700 dark:bg-neutral-950" />
          <button type="submit" disabled={loading || !input.trim() || remaining === 0} className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white disabled:opacity-40"><Send className="h-4 w-4" /></button>
        </form>
        <p className="mx-auto mt-2 flex max-w-3xl items-center gap-1.5 text-[11px] text-neutral-400"><ShieldAlert className="h-3 w-3" /> AI 基于公开数据生成，仅供研究参考，不构成投资建议。</p>
      </div>
    </div>
  );
}
