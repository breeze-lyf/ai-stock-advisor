"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { ArrowUp, Check, ChevronDown, Copy, Globe2, KeyRound, LineChart, MessageSquarePlus, PieChart, Plug, ShieldAlert, Sparkles, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";
import { AgentHomePanel } from "@/features/agent/components/AgentHomePanel";
import { BRAND } from "@/shared/config/features";
import {
  createAgentToken,
  getAgentConversation,
  listAgentConversations,
  sendAgentMessage,
  type AgentConversationSummary,
  type AgentSource,
  type AgentStep,
} from "@/features/agent/api";

const DISCLAIMER = "AI 基于公开数据生成，仅供研究参考，不构成投资建议。";
const SUGGESTIONS = [
  { icon: PieChart, tag: "持仓", q: "我的持仓今天表现怎么样？风险集中在哪？" },
  { icon: LineChart, tag: "技术面", q: "帮我看下 NVDA 的技术面和最近新闻" },
  { icon: Sparkles, tag: "估值", q: "600519 的估值贵不贵？" },
  { icon: Globe2, tag: "宏观", q: "最近有哪些宏观热点值得关注？" },
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  steps?: AgentStep[];
  sources?: AgentSource[];
  advice?: { ticker: string; direction: string; horizon_days: number }[];
  mode?: string;
}

const TOOL_LABELS: Record<string, string> = {
  get_quote: "实时报价",
  get_kline_and_technicals: "K线与技术指标",
  get_fundamentals: "基本面",
  search_news: "新闻检索",
  get_portfolio: "我的持仓",
  run_stock_diagnosis: "AI 深度诊断",
  macro_snapshot: "宏观快照",
};

const DIRECTION: Record<string, { label: string; cls: string }> = {
  BUY: { label: "买入", cls: "bg-up-soft text-up" },
  SELL: { label: "卖出", cls: "bg-down-soft text-down" },
  HOLD: { label: "持有", cls: "bg-elevated text-ink-2" },
};

function argSummary(args: Record<string, unknown>) {
  const v = args.ticker ?? args.symbol ?? args.query ?? Object.values(args)[0];
  return v === undefined ? "" : String(v).slice(0, 24);
}

/** 工具调用：一行紧凑的 chip，点击展开详情。 */
export function ToolSteps({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!steps.length) return null;
  const total = steps.reduce((a, s) => a + (s.duration_ms || 0), 0);
  return (
    <div className="mb-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="eyebrow mr-1">已调用 {steps.length} 个工具 · {(total / 1000).toFixed(1)}s</span>
        {steps.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setOpen(open === i ? null : i)}
            className={clsx(
              "inline-flex h-6 items-center gap-1 rounded-md border px-2 text-[11.5px] transition-colors",
              open === i ? "border-line-strong bg-elevated text-ink" : "border-line bg-surface text-ink-2 hover:bg-elevated",
            )}
          >
            {s.ok ? <Check className="h-3 w-3 text-emerald-500" /> : <X className="h-3 w-3 text-ink-3" />}
            {TOOL_LABELS[s.tool] || s.tool}
            {argSummary(s.arguments) && <span className="text-ink-3">· {argSummary(s.arguments)}</span>}
            <ChevronDown className={clsx("h-3 w-3 text-ink-3 transition-transform", open === i && "rotate-180")} />
          </button>
        ))}
      </div>
      {open !== null && steps[open] && (
        <div className="mt-2 rounded-lg border border-line bg-elevated/60 p-2.5 text-[11.5px]">
          <div className="mb-1.5 flex items-center gap-2 text-ink-3">
            <code className="truncate">{JSON.stringify(steps[open].arguments)}</code>
            <span className="num ml-auto shrink-0">{steps[open].duration_ms} ms</span>
          </div>
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ink-2">{steps[open].result_preview}</pre>
        </div>
      )}
    </div>
  );
}

/** 来源：编号小标签。 */
export function Sources({ sources }: { sources: AgentSource[] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-4 border-t border-line pt-3">
      <p className="eyebrow mb-2">来源</p>
      <div className="flex flex-wrap gap-1.5">
        {sources.slice(0, 10).map((s, i) => {
          const body = (
            <>
              <span className="num flex h-4 min-w-4 items-center justify-center rounded bg-elevated px-1 text-[10px] text-ink-3">{i + 1}</span>
              <span className="max-w-[16rem] truncate">{s.title}</span>
            </>
          );
          return s.url && s.url.startsWith("http") ? (
            <a key={i} href={s.url} target="_blank" rel="noreferrer" className="inline-flex h-6 items-center gap-1.5 rounded-md border border-line pl-1 pr-2 text-[11.5px] text-ink-2 hover:border-line-strong hover:text-ink">{body}</a>
          ) : (
            <span key={i} className="inline-flex h-6 items-center gap-1.5 rounded-md border border-line pl-1 pr-2 text-[11.5px] text-ink-3">{body}</span>
          );
        })}
      </div>
    </div>
  );
}

export function AssistantAvatar() {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand text-brand-fg shadow-sm">
      <Sparkles className="h-3.5 w-3.5" />
    </div>
  );
}

export function ThinkingRow({ label = "智能体正在调用工具分析" }: { label?: string }) {
  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="flex-1 space-y-2.5 pt-1">
        <p className="flex items-center gap-2 text-[13px] text-ink-3">
          {label}
          <span className="flex gap-0.5">{[0, 1, 2].map((i) => <span key={i} className="h-1 w-1 animate-bounce rounded-full bg-ink-3" style={{ animationDelay: `${i * 120}ms` }} />)}</span>
        </p>
        <div className="skeleton h-3 w-11/12" />
        <div className="skeleton h-3 w-9/12" />
        <div className="skeleton h-3 w-10/12" />
      </div>
    </div>
  );
}

function greeting() {
  const h = new Date().getHours();
  return h < 6 ? "夜深了" : h < 11 ? "早上好" : h < 13 ? "中午好" : h < 18 ? "下午好" : "晚上好";
}

export default function AgentWorkspace() {
  const { isAuthenticated } = useAuth();
  const { user: userProfile, portfolio } = useDashboardPortfolioData(isAuthenticated);
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<AgentConversationSummary[] | null>(null);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isAuthenticated) listAgentConversations().then(setConversations).catch(() => setConversations([]));
  }, [isAuthenticated, conversationId]);

  useEffect(() => {
    if (messages.length > 0 || loading) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [input]);

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const r = await sendAgentMessage(msg, conversationId);
      setConversationId(r.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: r.answer, steps: r.steps, sources: r.sources, mode: r.mode, advice: r.advice }]);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "请求失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const openConversation = async (id: string) => {
    try {
      const c = await getAgentConversation(id);
      setConversationId(c.id);
      setMessages(c.messages.map((m) => ({ role: m.role, content: m.content, steps: m.trace?.steps, sources: m.trace?.sources })));
    } catch {
      setError("加载会话失败");
    }
  };

  const issueToken = async () => {
    try {
      const t = await createAgentToken("MCP");
      setNewToken(t.token);
    } catch {
      setError("生成 Token 失败");
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-canvas">
      <DashboardHeader user={userProfile} activeTab={"analysis"} setActiveTab={(tab: DashboardTab) => router.push(`/dashboard?tab=${tab}`)} />
      <main className="flex min-h-0 flex-1">
        {/* ---------- left: conversations + MCP ---------- */}
        <aside className="hidden w-64 shrink-0 flex-col border-r border-line bg-surface lg:flex">
          <div className="p-3">
            <button type="button" onClick={() => { setConversationId(null); setMessages([]); setError(null); }} className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-ink text-[13px] font-medium text-canvas transition-opacity hover:opacity-90">
              <MessageSquarePlus className="h-4 w-4" /> 新对话
            </button>
          </div>
          <p className="eyebrow px-4 pb-1.5 pt-2">最近对话</p>
          <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
            {conversations === null && [0, 1, 2, 3].map((i) => <div key={i} className="skeleton mx-2 my-2 h-4" />)}
            {conversations?.length === 0 && <p className="px-2 py-1 text-[12px] text-ink-3">还没有对话</p>}
            {conversations?.map((c) => (
              <button key={c.id} type="button" onClick={() => openConversation(c.id)} className={clsx("flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors", c.id === conversationId ? "bg-elevated text-ink" : "text-ink-2 hover:bg-elevated/70")}>
                {c.channel === "mcp" && <span className="rounded bg-brand-soft px-1 text-[9.5px] font-semibold text-brand">MCP</span>}
                <span className="truncate">{c.title || "未命名对话"}</span>
              </button>
            ))}
          </div>
          <div className="m-3 rounded-xl border border-line bg-elevated/50 p-3">
            <p className="flex items-center gap-1.5 text-[12.5px] font-medium text-ink"><Plug className="h-3.5 w-3.5 text-brand" /> MCP 接入</p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-ink-3">在 Claude、Cursor、钉钉等客户端添加 <code className="rounded bg-surface px-1">/mcp</code>，用个人 Token 鉴权。</p>
            {newToken ? (
              <div className="mt-2 space-y-1.5">
                <p className="text-[11px] text-amber-600 dark:text-amber-400">仅显示一次，请立即保存</p>
                <button type="button" onClick={() => { navigator.clipboard?.writeText(newToken); setCopied(true); }} className="flex w-full items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-1.5 text-left font-mono text-[10.5px] text-ink-2">
                  <span className="truncate">{newToken}</span>
                  {copied ? <Check className="h-3 w-3 shrink-0 text-emerald-500" /> : <Copy className="h-3 w-3 shrink-0" />}
                </button>
              </div>
            ) : (
              <button type="button" onClick={issueToken} className="mt-2 inline-flex h-7 items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 text-[12px] text-ink-2 hover:text-ink">
                <KeyRound className="h-3.5 w-3.5" /> 生成个人 Token
              </button>
            )}
          </div>
        </aside>

        {/* ---------- center: chat ---------- */}
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto">
            <div className={clsx("mx-auto max-w-3xl px-4 sm:px-6", empty ? "pb-6 pt-10 sm:pt-16" : "space-y-8 py-8")}>
              {empty && (
                <div>
                  <p className="text-[13px] font-medium text-brand">{BRAND.name}</p>
                  <h1 className="mt-2 text-[26px] font-semibold tracking-tight text-ink sm:text-[30px]">{greeting()}，今天想看点什么？</h1>
                  <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-ink-3">我记得你的持仓、自选和投资画像，会实时调用行情、技术面、基本面、新闻与宏观数据回答；每条建议都会进入「复盘战绩」接受检验。</p>
                  <div className="mt-7 grid gap-2.5 sm:grid-cols-2">
                    {SUGGESTIONS.map(({ icon: Icon, tag, q }) => (
                      <button key={q} type="button" onClick={() => send(q)} className="card group flex items-start gap-3 p-3.5 text-left transition-all hover:-translate-y-px hover:border-line-strong hover:shadow-float">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-elevated text-ink-2 transition-colors group-hover:bg-brand-soft group-hover:text-brand"><Icon className="h-4 w-4" /></span>
                        <span>
                          <span className="eyebrow">{tag}</span>
                          <span className="mt-0.5 block text-[13.5px] leading-snug text-ink">{q}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="mt-8 xl:hidden">
                    <AgentHomePanel portfolio={portfolio} onAsk={(q) => send(q)} variant="inline" />
                  </div>
                </div>
              )}
              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[14px] leading-relaxed text-canvas">{m.content}</div>
                  </div>
                ) : (
                  <div key={i} className="flex gap-3">
                    <AssistantAvatar />
                    <div className="min-w-0 flex-1 pt-0.5">
                      {m.steps && <ToolSteps steps={m.steps} />}
                      {m.mode === "no_tools_fallback" && <p className="mb-2 text-[12px] text-amber-600">当前模型不支持工具调用，已降级为预取数据模式。</p>}
                      <div className="prose-agent"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
                      {m.advice && m.advice.length > 0 && (
                        <div className="mt-3 flex flex-wrap items-center gap-1.5 rounded-lg border border-line bg-elevated/50 px-3 py-2 text-[12px]">
                          <span className="text-ink-3">已记入复盘</span>
                          {m.advice.map((a, j) => (
                            <span key={j} className="inline-flex items-center gap-1 rounded-md border border-line bg-surface px-1.5 py-0.5">
                              <span className="font-medium text-ink">{a.ticker}</span>
                              <span className={clsx("rounded px-1 text-[10.5px] font-medium", DIRECTION[a.direction]?.cls)}>{DIRECTION[a.direction]?.label ?? a.direction}</span>
                              <span className="num text-ink-3">{a.horizon_days}天</span>
                            </span>
                          ))}
                          <Link href="/review" className="ml-auto text-brand hover:underline">查看战绩 →</Link>
                        </div>
                      )}
                      {m.sources && <Sources sources={m.sources} />}
                    </div>
                  </div>
                ),
              )}
              {loading && <ThinkingRow />}
              {error && <p className="rounded-lg border border-down/30 bg-down-soft px-3 py-2 text-[13px] text-down">{error}</p>}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="px-4 pb-4 pt-2 sm:px-6">
            <form className="mx-auto max-w-3xl" onSubmit={(e) => { e.preventDefault(); send(); }}>
              <div className="card flex items-end gap-2 p-2 pl-4 shadow-float focus-within:border-line-strong">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }}
                  rows={1}
                  maxLength={4000}
                  aria-label="向智能体提问"
                  placeholder="问问智能体，例如：0700.HK 最近走势和风险如何？"
                  className="max-h-44 min-h-[36px] flex-1 resize-none bg-transparent py-2 text-[14px] leading-relaxed text-ink outline-none placeholder:text-ink-3"
                />
                <button type="submit" aria-label="发送" disabled={loading || !input.trim()} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink text-canvas transition-opacity disabled:opacity-25">
                  <ArrowUp className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-2 flex items-center justify-center gap-1.5 text-[11px] text-ink-3"><ShieldAlert className="h-3 w-3" /> {DISCLAIMER} · Enter 发送，Shift+Enter 换行</p>
            </form>
          </div>
        </section>

        {/* ---------- right rail ---------- */}
        <AgentHomePanel portfolio={portfolio} onAsk={(q) => send(q)} />
      </main>
    </div>
  );
}

