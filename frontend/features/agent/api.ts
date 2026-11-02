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
