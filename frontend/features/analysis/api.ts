import type { AnalysisResponse, PortfolioAnalysisResponse } from "@/types";
import api from "@/shared/api/client";

function normalizeRrRatio(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const colonMatch = value.match(/[:：]\s*(\d+(?:\.\d+)?)/);
  if (colonMatch) {
    return Number(colonMatch[1]).toFixed(2);
  }

  const numberMatch = value.match(/(\d+(?:\.\d+)?)/);
  if (numberMatch) {
    return Number(numberMatch[1]).toFixed(2);
  }

  return undefined;
}

function parseRawAnalysis(result: Record<string, unknown>): AnalysisResponse | null {
  const raw = typeof result.analysis === "string" ? result.analysis : null;
  if (!raw) {
    return null;
  }

  try {
    const normalized = raw.startsWith("```json")
      ? raw.replace("```json", "").replace("```", "")
      : raw;
    const parsed = JSON.parse(normalized) as AnalysisResponse;
    return {
      ...parsed,
      is_cached: Boolean(result.is_cached),
      created_at: typeof result.created_at === "string" ? result.created_at : undefined,
      model_used: typeof result.model_used === "string" ? result.model_used : undefined,
    };
  } catch {
    return {
      ticker: typeof result.ticker === "string" ? result.ticker : "",
      technical_analysis: raw,
      fundamental_news: "Raw output",
      summary_status: "调用失败",
      is_cached: Boolean(result.is_cached),
      created_at: typeof result.created_at === "string" ? result.created_at : undefined,
      model_used: typeof result.model_used === "string" ? result.model_used : undefined,
    };
  }
}

export function normalizeAnalysisResponse(result: Record<string, unknown>): AnalysisResponse {
  if (typeof result.technical_analysis === "string") {
    return {
      ticker: typeof result.ticker === "string" ? result.ticker : "",
      decision_mode: typeof result.decision_mode === "string" ? result.decision_mode : undefined,
      dominant_driver: typeof result.dominant_driver === "string" ? result.dominant_driver : undefined,
      trade_setup_status: typeof result.trade_setup_status === "string" ? result.trade_setup_status : undefined,
      sentiment_score: typeof result.sentiment_score === "number" ? result.sentiment_score : undefined,
      summary_status: typeof result.summary_status === "string" ? result.summary_status : undefined,
      risk_level: typeof result.risk_level === "string" ? result.risk_level : undefined,
      trigger_condition: typeof result.trigger_condition === "string" ? result.trigger_condition : undefined,
      invalidation_condition: typeof result.invalidation_condition === "string" ? result.invalidation_condition : undefined,
      next_review_point: typeof result.next_review_point === "string" ? result.next_review_point : undefined,
      technical_analysis: result.technical_analysis,
      fundamental_news: typeof result.fundamental_news === "string" ? result.fundamental_news : undefined,
      news_summary: typeof result.news_summary === "string" ? result.news_summary : undefined,
      fundamental_analysis: typeof result.fundamental_analysis === "string" ? result.fundamental_analysis : undefined,
      macro_risk_note: typeof result.macro_risk_note === "string" ? result.macro_risk_note : undefined,
      add_on_trigger: typeof result.add_on_trigger === "string" ? result.add_on_trigger : undefined,
      action_advice: typeof result.action_advice === "string" ? result.action_advice : undefined,
      investment_horizon: typeof result.investment_horizon === "string" ? result.investment_horizon : undefined,
      confidence_level: typeof result.confidence_level === "number" ? result.confidence_level : undefined,
      immediate_action: typeof result.immediate_action === "string" ? result.immediate_action : undefined,
      target_price: typeof result.target_price === "number" ? result.target_price : undefined,
      target_price_1: typeof result.target_price_1 === "number" ? result.target_price_1 : undefined,
      target_price_2: typeof result.target_price_2 === "number" ? result.target_price_2 : undefined,
      stop_loss_price: typeof result.stop_loss_price === "number" ? result.stop_loss_price : undefined,
      max_position_pct: typeof result.max_position_pct === "number" ? result.max_position_pct : undefined,
      entry_zone: typeof result.entry_zone === "string" ? result.entry_zone : undefined,
      entry_price_low: typeof result.entry_price_low === "number" ? result.entry_price_low : undefined,
      entry_price_high: typeof result.entry_price_high === "number" ? result.entry_price_high : undefined,
      rr_ratio: normalizeRrRatio(result.rr_ratio),
      bull_case: typeof result.bull_case === "string" ? result.bull_case : undefined,
      base_case: typeof result.base_case === "string" ? result.base_case : undefined,
      bear_case: typeof result.bear_case === "string" ? result.bear_case : undefined,
      is_cached: Boolean(result.is_cached),
      model_used: typeof result.model_used === "string" ? result.model_used : undefined,
      created_at: typeof result.created_at === "string" ? result.created_at : undefined,
    };
  }

  return (
    parseRawAnalysis(result) || {
      ticker: typeof result.ticker === "string" ? result.ticker : "",
      summary_status: "无可用分析结果",
      technical_analysis: "当前未返回结构化分析数据。",
      is_cached: Boolean(result.is_cached),
      created_at: typeof result.created_at === "string" ? result.created_at : undefined,
      model_used: typeof result.model_used === "string" ? result.model_used : undefined,
    }
  );
}

export async function analyzeStock(ticker: string, force = false): Promise<AnalysisResponse> {
  const response = await api.post(`/api/v1/analysis/${ticker}?force=${force}`, undefined, {
    timeout: 240_000, // AI analysis can take up to 180s on the backend
  });
  return normalizeAnalysisResponse(response.data);
}

export async function getLatestAnalysis(ticker: string): Promise<AnalysisResponse | null> {
  try {
    const response = await api.get(`/api/v1/analysis/${ticker}`);
    return normalizeAnalysisResponse(response.data);
  } catch (error: unknown) {
    const axiosErr = error as { response?: { status?: number } };
    if (axiosErr.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function getAnalysisHistory(ticker: string): Promise<AnalysisResponse[]> {
  const response = await api.get(`/api/v1/analysis/${ticker}/history`);
  return response.data.map((item: Record<string, unknown>) => normalizeAnalysisResponse(item));
}

export async function analyzePortfolio(): Promise<PortfolioAnalysisResponse> {
  const response = await api.post("/api/v1/analysis/portfolio", undefined, {
    timeout: 240_000, // portfolio analysis is also AI-driven
  });
  return response.data;
}

export async function getLatestPortfolioAnalysis(): Promise<PortfolioAnalysisResponse | null> {
  try {
    const response = await api.get("/api/v1/analysis/portfolio");
    return response.data;
  } catch (error: unknown) {
    const axiosErr = error as { response?: { status?: number } };
    if (axiosErr.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Stock Capsule API
// ---------------------------------------------------------------------------

export interface StockCapsuleData {
  ticker: string;
  capsule_type: string;
  content: string | null;
  source_count: number | null;
  model_used: string | null;
  updated_at: string | null;
}

export interface StockCapsulesData {
  ticker: string;
  news: StockCapsuleData | null;
  fundamental: StockCapsuleData | null;
  technical: StockCapsuleData | null;
}

export async function getStockCapsules(ticker: string): Promise<StockCapsulesData> {
  const response = await api.get(`/api/v1/analysis/${ticker}/capsule`);
  return response.data;
}

export async function refreshStockCapsules(ticker: string): Promise<StockCapsulesData> {
  const response = await api.post(`/api/v1/analysis/${ticker}/capsule/refresh`, undefined, {
    timeout: 120_000, // capsule generation is AI-driven but lighter than full analysis
  });
  return response.data;
}
