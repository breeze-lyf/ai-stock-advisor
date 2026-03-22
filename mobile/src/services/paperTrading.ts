import httpClient from './client'

export type TradeStatus =
  | 'OPEN'
  | 'CLOSED_PROFIT'
  | 'CLOSED_LOSS'
  | 'CLOSED_MANUAL'

export interface SimulatedTrade {
  id: string
  user_id: string
  ticker: string
  status: TradeStatus
  entry_date: string
  entry_price: number
  entry_reason?: string | null
  target_price?: number | null
  stop_loss_price?: number | null
  current_price?: number | null
  unrealized_pnl_pct?: number | null
  exit_date?: string | null
  exit_price?: number | null
  realized_pnl_pct?: number | null
  exit_reason?: string | null
}

export interface CreateSimulatedTradeRequest {
  ticker: string
  entry_price: number
  entry_reason: string
  target_price?: number
  stop_loss_price?: number
}

export const paperTradingApi = {
  getTrades: async (status?: TradeStatus): Promise<SimulatedTrade[]> => {
    const query = status ? `?status=${encodeURIComponent(status)}` : ''
    return httpClient.get<SimulatedTrade[]>(`/paper-trading/${query}`)
  },

  createTrade: async (
    params: CreateSimulatedTradeRequest
  ): Promise<{ message: string; trade_id: string }> => {
    const query = new URLSearchParams()
    query.append('ticker', params.ticker)
    query.append('entry_price', params.entry_price.toString())
    query.append('entry_reason', params.entry_reason)
    if (params.target_price !== undefined) {
      query.append('target_price', params.target_price.toString())
    }
    if (params.stop_loss_price !== undefined) {
      query.append('stop_loss_price', params.stop_loss_price.toString())
    }
    return httpClient.post<{ message: string; trade_id: string }>(
      `/paper-trading/?${query.toString()}`
    )
  },
}

export default paperTradingApi
