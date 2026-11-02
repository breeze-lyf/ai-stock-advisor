import api from "@/shared/api/client";

export interface AgentStep {
  tool: string;
  arguments: Record<string, unknown>;
  ok: boolean;
  duration_ms: number;
  result_preview: string;
}

export interface AgentSource {
  title: string;
  url?: string | null;
  kind: string;
}

export interface AgentChatResponse {
  conversation_id: string;
  answer: string;
  steps: AgentStep[];
  sources: AgentSource[];
  mode: "tools" | "no_tools_fallback" | "error";
  stopped_reason: string;
  model?: { model: string; source: string } | null;
  disclaimer: string;
  advice?: { id?: string; ticker: string; direction: "BUY" | "SELL" | "HOLD"; horizon_days: number; price_at?: number | null }[];
}

export interface AgentConversationSummary {
  id: string;
  title: string | null;
  channel: string;
  updated_at: string;
}

export interface AgentTokenInfo {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

export async function sendAgentMessage(message: string, conversationId?: string | null): Promise<AgentChatResponse> {
  const res = await api.post<AgentChatResponse>(
    "/api/v1/agent/chat",
    { message, conversation_id: conversationId || undefined },
    { timeout: 240000 },
  );
  return res.data;
}

export async function listAgentConversations(): Promise<AgentConversationSummary[]> {
  return (await api.get<AgentConversationSummary[]>("/api/v1/agent/conversations")).data;
}

export async function getAgentConversation(id: string) {
  return (await api.get<{
    id: string;
    title: string | null;
    messages: { role: "user" | "assistant"; content: string; created_at: string; trace: { steps: AgentStep[]; sources: AgentSource[] } | null }[];
  }>(`/api/v1/agent/conversations/${id}`)).data;
}

export async function createAgentToken(name: string) {
  return (await api.post<{ id: string; token: string; prefix: string; note: string }>("/api/v1/agent/tokens", { name })).data;
}

export async function listAgentTokens(): Promise<AgentTokenInfo[]> {
  return (await api.get<AgentTokenInfo[]>("/api/v1/agent/tokens")).data;
}

export async function revokeAgentToken(id: string) {
  return (await api.delete(`/api/v1/agent/tokens/${id}`)).data;
}

// ---------------------------------------------------------------- P2
export interface DailyBrief {
  id: string;
  date: string;
  title: string;
  content: string;
  status: "ok" | "error";
  tickers: string[];
  pushed_channels: string | null;
  created_at: string;
}

export interface BriefList {
  items: DailyBrief[];
  scheduled: boolean;
  hour: number;
  disclaimer: string;
}

export async function listBriefs(limit = 14): Promise<BriefList> {
  return (await api.get("/api/v1/agent/briefs", { params: { limit } })).data;
}

export async function generateBrief(push = false): Promise<DailyBrief> {
  return (await api.post("/api/v1/agent/briefs/generate", null, { params: { push }, timeout: 300000 })).data;
}

export interface NotifierConfig {
  id: string;
  kind: "dingtalk" | "webhook" | "telegram";
  url: string | null;
  has_secret: boolean;
  enabled: boolean;
  brief_enabled: boolean;
  last_status: string | null;
}

export async function listNotifiers(): Promise<NotifierConfig[]> {
  return (await api.get("/api/v1/agent/notifiers")).data;
}

export async function createNotifier(body: { kind: string; url: string; secret?: string }): Promise<NotifierConfig> {
  return (await api.post("/api/v1/agent/notifiers", body)).data;
}

export async function deleteNotifier(id: string): Promise<void> {
  await api.delete(`/api/v1/agent/notifiers/${id}`);
}

export async function testNotifier(id: string): Promise<{ ok: boolean; message: string }> {
  return (await api.post(`/api/v1/agent/notifiers/${id}/test`)).data;
}

export interface AdviceRecord {
  id: string;
  ticker: string;
  direction: "BUY" | "SELL" | "HOLD";
  price_at: number | null;
  horizon_days: number;
  rationale: string | null;
  source: string;
  status: "open" | "evaluated" | "error";
  due_at: string;
  eval_price: number | null;
  return_pct: number | null;
  hit: boolean | null;
  created_at: string;
}

export interface AdviceStats {
  total: number;
  open: number;
  evaluated: number;
  hits: number;
  hit_rate: number | null;
  avg_directional_return_pct: number | null;
  by_direction: Record<string, { evaluated: number; hits: number }>;
}

export async function listAdvice(): Promise<{ items: AdviceRecord[]; stats: AdviceStats; disclaimer: string }> {
  return (await api.get("/api/v1/agent/advice")).data;
}

export interface PublicConfig {
  trial_enabled: boolean;
  trial_daily_limit: number;
  billing_enabled: boolean;
  brief_scheduled: boolean;
}

export async function getPublicConfig(): Promise<PublicConfig> {
  return (await api.get("/api/v1/agent/public-config")).data;
}

export async function sendTrialMessage(message: string): Promise<Omit<AgentChatResponse, "conversation_id"> & { remaining: number }> {
  return (await api.post("/api/v1/agent/trial/chat", { message }, { timeout: 180000 })).data;
}

export interface InvestmentProfile {
  risk_tolerance: "CONSERVATIVE" | "MODERATE" | "AGGRESSIVE";
  risk_tolerance_score: number;
  investment_experience: "BEGINNER" | "INTERMEDIATE" | "ADVANCED";
  preferred_markets: string[];
  default_market?: string;
  investment_style?: string | null;
  investment_horizon?: string | null;
}

/** 投资画像（智能体的长期记忆，会注入到系统提示词）。 */
export async function getInvestmentProfile(): Promise<InvestmentProfile | null> {
  return (await api.get("/api/v1/user-profile/profile")).data.profile;
}

export async function saveInvestmentProfile(p: InvestmentProfile): Promise<void> {
  const params: Record<string, string | number> = {
    risk_tolerance: p.risk_tolerance,
    risk_tolerance_score: p.risk_tolerance_score,
    investment_experience: p.investment_experience,
    preferred_markets: (p.preferred_markets.length ? p.preferred_markets : ["US"]).join(","),
    default_market: p.default_market || p.preferred_markets[0] || "US",
  };
  if (p.investment_style) params.investment_style = p.investment_style;
  if (p.investment_horizon) params.investment_horizon = p.investment_horizon;
  await api.post("/api/v1/user-profile/profile", null, { params });
}
