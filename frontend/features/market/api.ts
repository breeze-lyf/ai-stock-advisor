import api from "@/shared/api/client";
import type { PortfolioItem } from "@/types";

export async function fetchStockHistory(ticker: string, period = "1y", endDate?: string) {
  let url = `/api/v1/stocks/${ticker}/history?period=${period}`;
  if (endDate) {
    url += `&end_date=${endDate}`;
  }
  const response = await api.get(url);
  return response.data;
}

export async function fetchStockSnapshot(ticker: string): Promise<PortfolioItem> {
  const response = await api.get(`/api/v1/stocks/${ticker}`);
  return response.data;
}

export async function refreshAllStocks(priceOnly = false): Promise<{ message: string; updated_count: number }> {
  const response = await api.post(`/api/v1/stocks/refresh_all?price_only=${priceOnly}`);
  return response.data;
}
