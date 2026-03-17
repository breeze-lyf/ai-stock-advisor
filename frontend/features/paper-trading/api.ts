import type { SimulatedTrade, TradeStatus } from "@/types";
import api from "@/shared/api/client";

export async function getSimulatedTrades(status?: TradeStatus): Promise<SimulatedTrade[]> {
  const query = status ? `?status=${status}` : "";
  const response = await api.get(`/api/v1/paper-trading${query}`);
  return response.data;
}

export interface CreateSimulatedTradeRequest {
  ticker: string;
  entry_price: number;
  entry_reason: string;
  target_price?: number;
  stop_loss_price?: number;
}

export async function createSimulatedTrade(
  params: CreateSimulatedTradeRequest
): Promise<{ message: string; trade_id: number }> {
  const urlParams = new URLSearchParams();
  urlParams.append("ticker", params.ticker);
  urlParams.append("entry_price", params.entry_price.toString());
  urlParams.append("entry_reason", params.entry_reason);
  if (params.target_price) {
    urlParams.append("target_price", params.target_price.toString());
  }
  if (params.stop_loss_price) {
    urlParams.append("stop_loss_price", params.stop_loss_price.toString());
  }

  const response = await api.post(`/api/v1/paper-trading/?${urlParams.toString()}`);
  return response.data;
}
