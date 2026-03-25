import type { PortfolioItem, PortfolioSummary, SearchResult } from "@/types";
import api from "@/shared/api/client";
import type { AxiosRequestConfig } from "axios";

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await api.get("/api/v1/portfolio/summary");
  return response.data;
}

export async function getPortfolio(refresh = false, priceOnly = false): Promise<PortfolioItem[]> {
  const response = await api.get(`/api/v1/portfolio/?refresh=${refresh}&price_only=${priceOnly}`);
  return response.data;
}

export async function addPortfolioItem(ticker: string, quantity: number, avg_cost: number) {
  const response = await api.post("/api/v1/portfolio/", { ticker, quantity, avg_cost });
  return response.data;
}

export async function deletePortfolioItem(ticker: string) {
  const response = await api.delete(`/api/v1/portfolio/${ticker}`);
  return response.data;
}

export async function refreshStock(ticker: string, priceOnly = false): Promise<Partial<PortfolioItem>> {
  const response = await api.post(`/api/v1/portfolio/${ticker}/refresh?price_only=${priceOnly}`);
  return response.data;
}

export async function searchStocks(
  query: string,
  remote = false,
  config?: AxiosRequestConfig,
): Promise<SearchResult[]> {
  const response = await api.get(`/api/v1/portfolio/search?query=${query}&remote=${remote}`, config);
  return response.data;
}

export async function fetchStockNews(ticker: string) {
  const response = await api.get(`/api/v1/portfolio/${ticker}/news`);
  return response.data;
}

export async function reorderPortfolio(orders: { ticker: string; sort_order: number }[]): Promise<{ message: string }> {
  const response = await api.patch("/api/v1/portfolio/reorder", orders);
  return response.data;
}
