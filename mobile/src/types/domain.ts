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
