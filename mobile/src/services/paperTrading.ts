import type { CreateSimulatedTradeRequest, SimulatedTrade, TradeStatus } from '@/types/domain'
import httpClient from './client'

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
