/**
 * 增强 AI 分析 Hooks
 * 支持情景分析、风险分析、多时间框架分析
 */
"use client";

import { useState, useCallback, useEffect } from "react";
import api from "@/shared/api/client";

export interface ScenarioAnalysisData {
  bull_case: {
    target_price: number;
    upside_percent: number;
    probability: number;
    timeframe: string;
    key_drivers: string[];
    description?: string;
  };
  base_case: {
    target_price: number;
    upside_percent: number;
    probability: number;
    timeframe: string;
    key_drivers: string[];
    description?: string;
  };
  bear_case: {
    target_price: number;
    downside_percent: number;
    probability: number;
    timeframe: string;
    risk_factors: string[];
    description?: string;
  };
}

export interface RiskAnalysisData {
  overall_risk_score: number;
  market_risk: {
    score: number;
    factors?: string[];
    level?: string;
    beta?: number;
    description?: string;
  };
  technical_risk: {
    score: number;
    factors?: string[];
    level?: string;
    rsi?: number;
    description?: string;
  };
  sector_risk: {
    score: number;
    factors?: string[];
    level?: string;
    description?: string;
  };
  company_risk: {
    score: number;
    factors?: string[];
    level?: string;
    description?: string;
  };
  risk_summary?: string;
  beta?: number;
  rsi?: number;
  volatility?: number;
}

export interface MultiTimeframeAnalysisData {
  short_term: {
    timeframe: string;
    trend: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    key_levels: number[];
    strategy: string;
    reference_ma?: string;
  };
  medium_term: {
    timeframe: string;
    trend: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    key_levels: number[];
    strategy: string;
    reference_ma?: string;
  };
  long_term: {
    timeframe: string;
    trend: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    key_levels: number[];
    strategy: string;
    reference_ma?: string;
  };
}

export interface EnhancedAnalysisData {
  scenario_analysis?: ScenarioAnalysisData;
  risk_analysis?: RiskAnalysisData;
  multi_timeframe?: MultiTimeframeAnalysisData;
}

interface ScenarioAnalysisResponse {
  scenario_analysis?: ScenarioAnalysisData;
}

interface RiskAnalysisResponse {
  risk_analysis?: RiskAnalysisData;
}

interface MultiTimeframeResponse {
  multi_timeframe_analysis?: MultiTimeframeAnalysisData;
}

interface EnhancedAnalysisResponse {
  scenario_analysis?: ScenarioAnalysisData | { error?: string };
  risk_analysis?: RiskAnalysisData | { error?: string };
  multi_timeframe_analysis?: MultiTimeframeAnalysisData | { error?: string };
}

function hasErrorPayload(value: unknown): value is { error?: string } {
  return typeof value === "object" && value !== null && "error" in value;
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function useEnhancedAnalysis(ticker: string | null) {
  const [data, setData] = useState<EnhancedAnalysisData | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarioAnalysis = useCallback(async () => {
    if (!ticker) return;
    try {
      setLoading("scenario");
      const response = await api.get<ScenarioAnalysisResponse>(`/api/v1/analysis/enhanced/${ticker}/scenario-analysis`);
      setData((prev) => ({ ...prev, scenario_analysis: response.data.scenario_analysis }));
      setError(null);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to fetch scenario analysis"));
    } finally {
      setLoading(null);
    }
  }, [ticker]);

  const fetchRiskAnalysis = useCallback(async () => {
    if (!ticker) return;
    try {
      setLoading("risk");
      const response = await api.get<RiskAnalysisResponse>(`/api/v1/analysis/enhanced/${ticker}/risk-analysis`);
      setData((prev) => ({ ...prev, risk_analysis: response.data.risk_analysis }));
      setError(null);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to fetch risk analysis"));
    } finally {
      setLoading(null);
    }
  }, [ticker]);

  const fetchMultiTimeframe = useCallback(async () => {
    if (!ticker) return;
    try {
      setLoading("timeframe");
      const response = await api.get<MultiTimeframeResponse>(`/api/v1/analysis/enhanced/${ticker}/multi-timeframe`);
      setData((prev) => ({ ...prev, multi_timeframe: response.data.multi_timeframe_analysis }));
      setError(null);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to fetch multi-timeframe analysis"));
    } finally {
      setLoading(null);
    }
  }, [ticker]);

  const fetchAll = useCallback(async () => {
    if (!ticker) return;
    try {
      setLoading("all");
      const response = await api.get<EnhancedAnalysisResponse>(`/api/v1/analysis/enhanced/${ticker}/enhanced-analysis`);
      setData({
        scenario_analysis: hasErrorPayload(response.data.scenario_analysis) ? undefined : response.data.scenario_analysis,
        risk_analysis: hasErrorPayload(response.data.risk_analysis) ? undefined : response.data.risk_analysis,
        multi_timeframe: hasErrorPayload(response.data.multi_timeframe_analysis) ? undefined : response.data.multi_timeframe_analysis,
      });
      setError(null);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to fetch enhanced analysis"));
    } finally {
      setLoading(null);
    }
  }, [ticker]);

  useEffect(() => {
    if (ticker) {
      fetchAll();
    } else {
      setData(null);
    }
  }, [ticker, fetchAll]);

  return {
    data,
    loading,
    error,
    fetchScenarioAnalysis,
    fetchRiskAnalysis,
    fetchMultiTimeframe,
    fetchAll,
    setData,
  };
}
