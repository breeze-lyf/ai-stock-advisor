"use client";

import { useState, useEffect } from "react";
import * as quantApi from "@/features/quant/api";
import type { QuantFactor, FactorICAnalysis, FactorLayeredBacktest } from "@/features/quant/api";

export function useQuantFactors() {
  const [factors, setFactors] = useState<QuantFactor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFactors = async (category?: string) => {
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
  };

  useEffect(() => {
    fetchFactors();
  }, []);

  return { factors, loading, error, refresh: fetchFactors };
}

export function useFactorICAnalysis(factorId: string, startDate: string, endDate: string) {
  const [data, setData] = useState<FactorICAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchICAnalysis = async (method = "rank", forwardPeriod = 5) => {
    if (!factorId) return;
    try {
      setLoading(true);
      const result = await quantApi.getFactorICAnalysis(factorId, startDate, endDate, forwardPeriod, method);
      setData(result);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch IC analysis");
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, fetchICAnalysis };
}

export function useFactorLayeredBacktest(factorId: string, startDate: string, endDate: string) {
  const [data, setData] = useState<FactorLayeredBacktest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBacktest = async (nLayers = 10) => {
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
  };

  return { data, loading, error, fetchBacktest };
}
