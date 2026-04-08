import api from "@/shared/api/client";

export interface SignalItem {
  id: string;
  ticker: string;
  signal_type: string;   // BUY / SELL / HOLD / WATCH
  signal_status: string; // ACTIVE / CLOSED / EXPIRED / CANCELLED
  entry_price: number;
  target_price?: number;
  stop_loss_price?: number;
  confidence_score: number;
  time_horizon: string;
  pnl_percent?: number;
  created_at: string;
  closed_at?: string;
}

export interface SignalPerformance {
  period: string;
  total_signals: number;
  closed_signals: number;
  winning_signals: number;
  losing_signals: number;
  win_rate: number;
  avg_pnl_percent: number;
  best_signal: { ticker: string | null; pnl_percent: number | null };
  worst_signal: { ticker: string | null; pnl_percent: number | null };
}

export async function getSignals(ticker?: string, limit = 10): Promise<SignalItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (ticker) params.set("ticker", ticker);
  const response = await api.get(`/api/v1/signals/signals?${params}`);
  return (response.data.signals as SignalItem[]) || [];
}

export async function getSignalPerformance(period = "ALL"): Promise<SignalPerformance> {
  const response = await api.get(`/api/v1/signals/performance?period=${period}`);
  return response.data.performance as SignalPerformance;
}
