/**
 * 量化因子 API 客户端 - 完整版
 */
import api from "@/shared/api/client";

export interface QuantFactor {
  id: string;
  name: string;
  code_name: string;
  category: string;
  description?: string;
  formula?: string;
  ic_mean?: number;
  ic_ir?: number;
  rank_ic_mean?: number;
  rank_ic_ir?: number;
  annual_return?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  turnover_rate?: number;
  is_public: boolean;
  is_custom: boolean;
}

export interface FactorICAnalysis {
  ic_series: Array<{ trade_date: string; ic: number }>;
  ic_mean: number;
  ic_ir: number;
  t_stat: number;
  sample_size: number;
}

export interface FactorLayeredBacktest {
  equity_curves: Record<string, Array<{ date: string; equity: number }>>;
  final_equity: Record<string, number>;
  long_short_return: number;
  layers: number;
}

export interface FactorTurnover {
  avg_turnover: number;
  turnover_series: Array<{ date: string; turnover: number }>;
}

export interface FactorDecay {
  ic_decay: Array<{ lag: number; ic_mean: number }>;
  half_life: number;
}

export interface PortfolioOptimizationResult {
  weights: Record<string, number>;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  success: boolean;
}

export interface BacktestResult {
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  volatility: number;
  total_trades: number;
  win_rate: number;
  equity_curve: Array<{ date: string; equity: number }>;
  monthly_returns: Record<string, number>;
}

export interface QuantStrategy {
  id: string;
  name: string;
  strategy_type: string;
  factor_weights: Record<string, number>;
  rebalance_frequency: string;
  is_active: boolean;
}

export interface TradingSignal {
  ticker: string;
  signal_strength: number;
  target_weight?: number;
}

export interface RiskCheckResult {
  violations: Array<{ type: string; ticker?: string; sector?: string; current_weight: number; limit: number }>;
  current_exposure: {
    tickers: Record<string, { market_value: number; weight: number }>;
    sectors: Record<string, number>;
  };
  compliant: boolean;
}

// ==================== 因子管理 ====================

export async function getFactors(category?: string, is_active = true): Promise<QuantFactor[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("is_active", String(is_active));
  const response = await api.get(`/api/v1/quant/factors?${params}`);
  return response.data.factors;
}

export async function getFactorDetail(factor_id: string): Promise<QuantFactor> {
  const response = await api.get(`/api/v1/quant/factors/${factor_id}`);
  return response.data;
}

export async function createFactor(factorData: {
  name: string;
  code_name: string;
  category: string;
  description?: string;
  formula?: string;
  calculation_params?: any;
  lookback_period?: number;
}): Promise<{ id: string; message: string }> {
  const response = await api.post("/api/v1/quant/factors", factorData);
  return response.data;
}

export async function deleteFactor(factor_id: string): Promise<void> {
  await api.delete(`/api/v1/quant/factors/${factor_id}`);
}

// ==================== 因子分析 ====================

export async function getFactorICAnalysis(
  factor_id: string,
  start_date: string,
  end_date: string,
  forward_period = 5,
  method = "rank",
): Promise<FactorICAnalysis> {
  const params = new URLSearchParams({
    start_date,
    end_date,
    forward_period: String(forward_period),
    method,
  });
  const response = await api.get(`/api/v1/quant/factors/${factor_id}/ic-analysis?${params}`);
  return response.data;
}

export async function getFactorLayeredBacktest(
  factor_id: string,
  start_date: string,
  end_date: string,
  n_layers = 10,
): Promise<FactorLayeredBacktest> {
  const params = new URLSearchParams({ start_date, end_date, n_layers: String(n_layers) });
  const response = await api.get(`/api/v1/quant/factors/${factor_id}/layered-backtest?${params}`);
  return response.data;
}

export async function getFactorTurnover(
  factor_id: string,
  start_date: string,
  end_date: string,
): Promise<FactorTurnover> {
  const params = new URLSearchParams({ start_date, end_date });
  const response = await api.get(`/api/v1/quant/factors/${factor_id}/turnover?${params}`);
  return response.data;
}

export async function getFactorDecay(
  factor_id: string,
  start_date: string,
  end_date: string,
  max_lag = 20,
): Promise<FactorDecay> {
  const params = new URLSearchParams({ start_date, end_date, max_lag: String(max_lag) });
  const response = await api.get(`/api/v1/quant/factors/${factor_id}/decay?${params}`);
  return response.data;
}

// ==================== 组合优化 ====================

export async function optimizePortfolio(config: {
  optimizer_type: "mean_variance" | "black_litterman" | "risk_parity" | "hrp" | "min_volatility" | "max_sharpe";
  expected_returns?: Record<string, number>;
  cov_matrix?: any;
  target_return?: number;
  target_volatility?: number;
  min_weight?: number;
  max_weight?: number;
  sector_constraints?: Record<string, number>;
  market_cap?: Record<string, number>;
  views?: Array<{ assets: string[]; view: number; confidence: number }>;
  returns?: any;
}): Promise<PortfolioOptimizationResult> {
  const response = await api.post("/api/v1/quant/optimize", config);
  return response.data;
}

// ==================== 量化回测 ====================

export async function runBacktest(config: {
  name: string;
  start_date: string;
  end_date: string;
  factor_ids?: string[];
  initial_capital?: number;
  commission_rate?: number;
  max_position_pct?: number;
  rebalance_frequency?: string;
}): Promise<BacktestResult> {
  const response = await api.post("/api/v1/quant/backtest/run", config);
  return response.data;
}

// ==================== 策略管理 ====================

export async function getStrategies(): Promise<QuantStrategy[]> {
  const response = await api.get("/api/v1/quant/strategies");
  return response.data.strategies;
}

export async function createStrategy(strategyData: {
  name: string;
  strategy_type: string;
  description?: string;
  factor_weights: Record<string, number>;
  rebalance_frequency?: string;
  max_position_pct?: number;
  max_stocks?: number;
  stop_loss_pct?: number;
}): Promise<{ id: string; message: string }> {
  const response = await api.post("/api/v1/quant/strategies", strategyData);
  return response.data;
}

export async function generateSignals(
  strategy_id: string,
  trade_date?: string,
): Promise<{ message: string; signals: TradingSignal[] }> {
  const params = trade_date ? `?trade_date=${trade_date}` : "";
  const response = await api.post(`/api/v1/quant/strategies/${strategy_id}/generate-signals${params}`);
  return response.data;
}

// ==================== 风险管理 ====================

export async function checkRisk(positions: {
  positions: Record<string, { quantity: number; price: number; sector?: string }>;
  portfolio_value: number;
}): Promise<RiskCheckResult> {
  const response = await api.post("/api/v1/quant/risk/check", positions);
  return response.data;
}

export async function getRiskReport(): Promise<{
  risk_level: string;
  position_analysis: any;
  risk_metrics: any;
  recommendations: string[];
}> {
  const response = await api.get("/api/v1/quant/risk/report");
  return response.data;
}
