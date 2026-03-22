import { create } from 'zustand'
import { portfolioApi } from '@/services/portfolio'

export interface PortfolioItem {
  ticker: string
  name: string
  quantity: number
  cost_basis: number
  price?: number | null
  weight?: number | null
  market_status?: string | null
}

export interface PortfolioSummary {
  total_market_value: number
  total_unrealized_pl: number
  total_pl_percent: number
  day_change: number
  holdings: PortfolioItem[]
}

interface PortfolioState {
  items: PortfolioItem[]
  summary: PortfolioSummary | null
  isLoading: boolean
  error: string | null
  
  // Actions
  fetchPortfolio: () => Promise<void>
  fetchSummary: () => Promise<void>
  addItem: (ticker: string, quantity: number, costBasis: number) => Promise<boolean>
  removeItem: (ticker: string) => Promise<boolean>
  refreshItem: (ticker: string) => Promise<void>
  refreshAll: () => Promise<void>
  clearError: () => void
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  items: [],
  summary: null,
  isLoading: false,
  error: null,

  fetchPortfolio: async () => {
    set({ isLoading: true, error: null })
    try {
      const items = await portfolioApi.getPortfolio()
      set({ items, isLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取持仓失败'
      set({ error: message, isLoading: false })
    }
  },

  fetchSummary: async () => {
    set({ isLoading: true, error: null })
    try {
      const summary = await portfolioApi.getSummary()
      set({ summary, isLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取组合概览失败'
      set({ error: message, isLoading: false })
    }
  },

  addItem: async (ticker: string, quantity: number, costBasis: number) => {
    set({ isLoading: true, error: null })
    try {
      await portfolioApi.addItem({ ticker, quantity, avg_cost: costBasis })
      // 重新获取列表
      await get().fetchPortfolio()
      return true
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '添加股票失败'
      set({ error: message, isLoading: false })
      return false
    }
  },

  removeItem: async (ticker: string) => {
    set({ isLoading: true, error: null })
    try {
      await portfolioApi.deleteItem(ticker)
      // 从本地状态中移除
      set((state) => ({
        items: state.items.filter((item) => item.ticker !== ticker),
        isLoading: false,
      }))
      return true
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除股票失败'
      set({ error: message, isLoading: false })
      return false
    }
  },

  refreshItem: async (ticker: string) => {
    try {
      const updatedItem = await portfolioApi.refreshItem(ticker)
      set((state) => ({
        items: state.items.map((item) =>
          item.ticker === ticker ? { ...item, ...updatedItem } : item
        ),
      }))
    } catch (error) {
      console.error('刷新股票数据失败:', error)
    }
  },

  refreshAll: async () => {
    set({ isLoading: true })
    try {
      await portfolioApi.refreshAll()
      await get().fetchPortfolio()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '刷新全部数据失败'
      set({ error: message, isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
