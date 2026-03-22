import type { PortfolioItem, PortfolioSummary } from '@/store/portfolioStore'
import httpClient from './client'

interface AddItemRequest {
  ticker: string
  quantity: number
  avg_cost: number
}

interface SearchResult {
  ticker: string
  name: string
}

interface PortfolioItemResponse {
  ticker: string
  name?: string | null
  quantity: number
  avg_cost: number
  current_price?: number | null
  pl_percent?: number | null
  market_status?: string | null
}

interface PortfolioSummaryResponse {
  total_market_value: number
  total_unrealized_pl: number
  total_pl_percent: number
  day_change: number
  holdings: PortfolioItemResponse[]
}

function mapPortfolioItem(item: PortfolioItemResponse): PortfolioItem {
  return {
    ticker: item.ticker,
    name: item.name || item.ticker,
    quantity: item.quantity,
    cost_basis: item.avg_cost,
    price: item.current_price ?? null,
    weight: item.pl_percent ?? null,
    market_status: item.market_status ?? null,
  }
}

export const portfolioApi = {
  /**
   * 获取投资组合列表
   */
  getPortfolio: async (): Promise<PortfolioItem[]> => {
    const items = await httpClient.get<PortfolioItemResponse[]>('/portfolio')
    return items.map(mapPortfolioItem)
  },

  /**
   * 获取投资组合概览
   */
  getSummary: async (): Promise<PortfolioSummary> => {
    const summary = await httpClient.get<PortfolioSummaryResponse>('/portfolio/summary')
    return {
      ...summary,
      holdings: summary.holdings.map(mapPortfolioItem),
    }
  },

  /**
   * 添加股票到组合
   */
  addItem: async (data: AddItemRequest): Promise<PortfolioItem> => {
    const item = await httpClient.post<PortfolioItemResponse>('/portfolio', data)
    return mapPortfolioItem(item)
  },

  /**
   * 删除组合中的股票
   */
  deleteItem: async (ticker: string): Promise<void> => {
    return httpClient.delete<void>(`/portfolio/${encodeURIComponent(ticker)}`)
  },

  /**
   * 刷新单只股票数据
   */
  refreshItem: async (ticker: string): Promise<PortfolioItem> => {
    const item = await httpClient.post<PortfolioItemResponse>(
      `/portfolio/${encodeURIComponent(ticker)}/refresh`
    )
    return mapPortfolioItem(item)
  },

  /**
   * 刷新全部股票数据
   */
  refreshAll: async (): Promise<void> => {
    return httpClient.post<void>('/stocks/refresh_all')
  },

  /**
   * 搜索股票
   */
  searchStocks: async (query: string): Promise<SearchResult[]> => {
    return httpClient.get<SearchResult[]>(
      `/portfolio/search?query=${encodeURIComponent(query)}&remote=true`
    )
  },
}

export default portfolioApi
