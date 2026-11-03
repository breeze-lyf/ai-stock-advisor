"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { Bot, ChevronDown, ChevronRight, KeyRound, Loader2, MessageSquarePlus, Send, ShieldAlert, Wrench, CheckCircle2, XCircle } from "lucide-react";
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
const SUGGESTIONS = ["帮我看下 NVDA 的技术面和最近新闻", "我的持仓今天表现怎么样？风险集中在哪？", "600519 的估值贵不贵？", "最近有哪些宏观热点值得关注？"];

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

export function ToolSteps({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="mb-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/60 text-xs">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2 text-neutral-600 dark:text-neutral-400">
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        <Wrench className="h-3.5 w-3.5" />
        调用了 {steps.length} 个工具：{steps.map((s) => TOOL_LABELS[s.tool] || s.tool).join(" → ")}
      </button>
      {open && (
        <ul className="space-y-2 border-t border-neutral-200 dark:border-neutral-800 px-3 py-2">
          {steps.map((s, i) => (
            <li key={i} className="space-y-1">
              <div className="flex items-center gap-2 font-medium text-neutral-700 dark:text-neutral-300">
                {s.ok ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <XCircle className="h-3.5 w-3.5 text-rose-500" />}
                {TOOL_LABELS[s.tool] || s.tool}
                <code className="text-[11px] text-neutral-500">{JSON.stringify(s.arguments)}</code>
                <span className="ml-auto text-neutral-400">{s.duration_ms} ms</span>
              </div>
              <pre className="max-h-32 overflow-auto whitespace-pre-wrap break-all rounded bg-white dark:bg-neutral-950 p-2 text-[11px] text-neutral-500">{s.result_preview}</pre>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Sources({ sources }: { sources: AgentSource[] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {sources.slice(0, 10).map((s, i) =>
        s.url && s.url.startsWith("http") ? (
          <a key={i} href={s.url} target="_blank" rel="noreferrer" className="rounded-full border border-blue-200 dark:border-blue-900 px-2 py-0.5 text-[11px] text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20">
            {s.title}
          </a>
        ) : (
          <span key={i} className="rounded-full border border-neutral-200 dark:border-neutral-800 px-2 py-0.5 text-[11px] text-neutral-500">{s.title}</span>
        ),
      )}
    </div>
  );
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
  const [conversations, setConversations] = useState<AgentConversationSummary[]>([]);
  const [newToken, setNewToken] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) listAgentConversations().then(setConversations).catch(() => undefined);
  }, [isAuthenticated, conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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

  return (
    <div className="h-screen bg-neutral-50 dark:bg-neutral-950 flex flex-col overflow-hidden">
      <DashboardHeader user={userProfile} activeTab={"analysis"} setActiveTab={(tab: DashboardTab) => router.push(`/dashboard?tab=${tab}`)} />
      <main className="flex-1 min-h-0 flex">
        <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
          <div className="p-3">
            <button type="button" onClick={() => { setConversationId(null); setMessages([]); }} className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
              <MessageSquarePlus className="h-4 w-4" /> 新对话
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2 space-y-1">
            {conversations.map((c) => (
              <button key={c.id} type="button" onClick={() => openConversation(c.id)} className={clsx("w-full truncate rounded-md px-3 py-2 text-left text-sm", c.id === conversationId ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800")}>
                {c.channel === "mcp" ? "[MCP] " : ""}{c.title || "未命名对话"}
              </button>
            ))}
          </div>
          <div className="border-t border-neutral-200 dark:border-neutral-800 p-3 text-xs text-neutral-500 space-y-2">
            <div className="flex items-center gap-1.5 font-medium text-neutral-700 dark:text-neutral-300"><KeyRound className="h-3.5 w-3.5" /> MCP 接入</div>
            <p>在钉钉数字员工 / Claude 等客户端添加 MCP 服务：<code>/mcp</code>，使用个人 Token 鉴权。</p>
            {newToken ? (
              <div className="space-y-1">
                <p className="text-amber-600">Token 仅显示一次，请立即复制保存：</p>
                <code className="block break-all rounded bg-neutral-100 dark:bg-neutral-800 p-2 text-[11px]">{newToken}</code>
              </div>
            ) : (
              <button type="button" onClick={issueToken} className="rounded-md border border-neutral-300 dark:border-neutral-700 px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-800">生成个人 Token</button>
            )}
          </div>
        </aside>

        <section className="flex-1 min-w-0 flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
              {messages.length === 0 && (
                <div className="pt-10 text-center space-y-4">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-white"><Bot className="h-6 w-6" /></div>
                  <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{BRAND.name}</h1>
                  <p className="text-sm text-neutral-500">它记得你的持仓、自选和投资画像，会自动调用行情、技术面、基本面、新闻与宏观数据回答问题；每条建议都会进入「复盘战绩」接受检验。</p>
                  <div className="grid gap-2 sm:grid-cols-2 pt-2">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} type="button" onClick={() => send(s)} className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 px-4 py-3 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:border-blue-300">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2.5 text-sm text-white whitespace-pre-wrap">{m.content}</div>
                  </div>
                ) : (
                  <div key={i} className="flex gap-3">
                    <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white"><Bot className="h-4 w-4" /></div>
                    <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 px-4 py-3">
                      {m.steps && <ToolSteps steps={m.steps} />}
                      {m.mode === "no_tools_fallback" && <p className="mb-2 text-xs text-amber-600">当前模型不支持工具调用，已降级为预取数据模式。</p>}
                      <div className="prose prose-sm dark:prose-invert max-w-none text-neutral-800 dark:text-neutral-200">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                      </div>
                      {m.sources && <Sources sources={m.sources} />}
                      {m.advice && m.advice.length > 0 && (
                        <p className="mt-2 text-[11px] text-neutral-400">已记入复盘：{m.advice.map((a) => `${a.ticker} ${a.direction} ${a.horizon_days}天`).join("，")} · <a href="/review" className="text-blue-600">查看战绩</a></p>
                      )}
                    </div>
                  </div>
                ),
              )}
              {loading && (
                <div className="flex items-center gap-2 text-sm text-neutral-500"><Loader2 className="h-4 w-4 animate-spin" /> 智能体正在调用工具分析中…</div>
              )}
              {error && <p className="text-sm text-rose-600">{error}</p>}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="border-t border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/80 px-4 py-3">
            <form className="mx-auto flex max-w-3xl items-end gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                rows={1}
                maxLength={4000}
                placeholder="问问智能体，例如：帮我看下 0700.HK 的走势和风险"
                className="flex-1 resize-none rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
              <button type="submit" disabled={loading || !input.trim()} className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white disabled:opacity-40">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </form>
            <p className="mx-auto mt-2 flex max-w-3xl items-center gap-1.5 text-[11px] text-neutral-400"><ShieldAlert className="h-3 w-3" /> {DISCLAIMER}</p>
          </div>
        </section>
        <AgentHomePanel portfolio={portfolio} onAsk={(q) => send(q)} />
      </main>
    </div>
  );
}
