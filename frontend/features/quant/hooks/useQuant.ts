"use client";

import { useState, useCallback } from "react";
import * as quantApi from "@/features/quant/api";

export function useQuantFactors() {
  const [factors, setFactors] = useState<quantApi.QuantFactor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFactors = useCallback(async (category?: string) => {
    try {
      setLoading(true);
      const data = await quantApi.getFactors(category);
      setFactors(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch factors");
    } finally {
      setLoading(false);
    }
  }, []);

  return { factors, loading, error, refresh: fetchFactors };
}

export function useFactorAnalysis(factorId: string, startDate: string, endDate: string) {
  const [icData, setIcData] = useState<quantApi.FactorICAnalysis | null>(null);
  const [turnoverData, setTurnoverData] = useState<quantApi.FactorTurnover | null>(null);
  const [decayData, setDecayData] = useState<quantApi.FactorDecay | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchICAnalysis = useCallback(async (method = "rank", forwardPeriod = 5) => {
    if (!factorId) return;
    try {
      setLoading("ic");
      const result = await quantApi.getFactorICAnalysis(factorId, startDate, endDate, forwardPeriod, method);
      setIcData(result);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch IC analysis");
    } finally {
      setLoading(null);
    }
  }, [factorId, startDate, endDate]);

  const fetchTurnover = useCallback(async () => {
    if (!factorId) return;
    try {
      setLoading("turnover");
      const result = await quantApi.getFactorTurnover(factorId, startDate, endDate);
      setTurnoverData(result);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch turnover");
    } finally {
      setLoading(null);
    }
  }, [factorId, startDate, endDate]);

  const fetchDecay = useCallback(async (maxLag = 20) => {
    if (!factorId) return;
    try {
      setLoading("decay");
      const result = await quantApi.getFactorDecay(factorId, startDate, endDate, maxLag);
      setDecayData(result);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch decay");
    } finally {
      setLoading(null);
    }
  }, [factorId, startDate, endDate]);

  return {
    icData,
    turnoverData,
    decayData,
    loading,
    error,
    fetchICAnalysis,
    fetchTurnover,
    fetchDecay,
  };
}

export function useFactorBacktest(factorId: string, startDate: string, endDate: string) {
  const [data, setData] = useState<quantApi.FactorLayeredBacktest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBacktest = useCallback(async (nLayers = 10) => {
    if (!factorId) return;
    try {
      setLoading(true);
      const result = await quantApi.getFactorLayeredBacktest(factorId, startDate, endDate, nLayers);
      setData(result);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch layered backtest");
    } finally {
      setLoading(false);
    }
  }, [factorId, startDate, endDate]);

  return { data, loading, error, fetchBacktest };
}

export function useStrategies() {
  const [strategies, setStrategies] = useState<quantApi.QuantStrategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStrategies = useCallback(async () => {
    try {
      setLoading(true);
      const data = await quantApi.getStrategies();
      setStrategies(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch strategies");
    } finally {
      setLoading(false);
    }
  }, []);

  const createStrategy = useCallback(async (strategyData: {
    name: string;
    strategy_type: string;
    factor_weights: Record<string, number>;
  }) => {
    try {
      const result = await quantApi.createStrategy(strategyData);
      await fetchStrategies();
      return result;
    } catch (e: any) {
      throw e;
    }
  }, [fetchStrategies]);

  const generateSignals = useCallback(async (strategyId: string) => {
    try {
      return await quantApi.generateSignals(strategyId);
    } catch (e: any) {
      throw e;
    }
  }, []);

  return { strategies, loading, error, refresh: fetchStrategies, createStrategy, generateSignals };
}

export function useBacktest() {
  const [result, setResult] = useState<quantApi.BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (config: {
    name: string;
    start_date: string;
    end_date: string;
    factor_ids?: string[];
    initial_capital?: number;
    commission_rate?: number;
    max_position_pct?: number;
    rebalance_frequency?: string;
  }) => {
    try {
      setLoading(true);
      const data = await quantApi.runBacktest(config);
      setResult(data);
      setError(null);
      return data;
    } catch (e: any) {
      setError(e.message || "Failed to run backtest");
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, run };
}

export function useOptimizer() {
  const [result, setResult] = useState<quantApi.PortfolioOptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const optimize = useCallback(async (config: {
    optimizer_type: "mean_variance" | "black_litterman" | "risk_parity" | "hrp" | "min_volatility" | "max_sharpe";
    expected_returns?: Record<string, number>;
    cov_matrix?: any;
    target_return?: number;
    target_volatility?: number;
  }) => {
    try {
      setLoading(true);
      const data = await quantApi.optimizePortfolio(config);
      setResult(data);
      setError(null);
      return data;
    } catch (e: any) {
      setError(e.message || "Failed to optimize");
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, optimize };
}
