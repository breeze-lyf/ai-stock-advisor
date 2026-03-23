import type { AnalysisResponse, PortfolioAnalysisResponse } from '@/types/domain'
import httpClient from './client'

export const analysisApi = {
  /**
   * 获取个股 AI 分析
   */
  analyzeStock: async (ticker: string, forceRefresh = false): Promise<AnalysisResponse> => {
    const params = forceRefresh ? '?force=true' : ''
    return httpClient.post<AnalysisResponse>(`/analysis/${encodeURIComponent(ticker)}${params}`)
  },

  /**
   * 获取最新分析（缓存）
   */
  getLatestAnalysis: async (ticker: string): Promise<AnalysisResponse | null> => {
    try {
      return await httpClient.get<AnalysisResponse>(`/analysis/${encodeURIComponent(ticker)}`)
    } catch {
      return null
    }
  },

  /**
   * 获取分析历史
   */
  getAnalysisHistory: async (ticker: string, limit = 10): Promise<AnalysisResponse[]> => {
    return httpClient.get<AnalysisResponse[]>(
      `/analysis/${encodeURIComponent(ticker)}/history?limit=${limit}`
    )
  },

  /**
   * 获取投资组合分析
   */
  analyzePortfolio: async (forceRefresh = false): Promise<PortfolioAnalysisResponse> => {
    void forceRefresh
    return httpClient.post<PortfolioAnalysisResponse>('/analysis/portfolio')
  },

  /**
   * 获取最新组合分析
   */
  getLatestPortfolioAnalysis: async (): Promise<PortfolioAnalysisResponse | null> => {
    try {
      return await httpClient.get<PortfolioAnalysisResponse>('/analysis/portfolio')
    } catch {
      return null
    }
  },
}

export default analysisApi
