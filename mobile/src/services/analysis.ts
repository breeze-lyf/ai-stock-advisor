import httpClient from './client'

export interface AnalysisResponse {
  ticker: string
  decision_mode?: string
  dominant_driver?: string
  trade_setup_status?: string
  sentiment_score?: number
  summary_status?: string
  core_logic_summary?: string
  risk_level?: string
  trigger_condition?: string
  invalidation_condition?: string
  next_review_point?: string
  technical_analysis?: string
  fundamental_news?: string
  news_summary?: string
  fundamental_analysis?: string
  macro_risk_note?: string
  add_on_trigger?: string
  action_advice?: string
  investment_horizon?: string
  confidence_level?: number
  immediate_action?: string
  target_price?: number
  target_price_1?: number
  target_price_2?: number
  stop_loss_price?: number
  max_position_pct?: number
  entry_zone?: string
  entry_price_low?: number
  entry_price_high?: number
  rr_ratio?: string
  bull_case?: string
  base_case?: string
  bear_case?: string
  is_cached?: boolean
  model_used?: string
  created_at?: string
}

export interface PortfolioAnalysisResponse {
  health_score: number
  risk_level: string
  summary: string
  diversification_analysis: string
  strategic_advice: string
  top_risks: string[]
  top_opportunities: string[]
  detailed_report: string
  model_used?: string
  created_at: string
}

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
