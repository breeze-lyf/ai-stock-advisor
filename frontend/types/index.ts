import { components } from "./schema";

export type PortfolioItem = components["schemas"]["PortfolioItem"] & {
    price?: number | null;
    resistance_1?: number | null;
    support_1?: number | null;
    atr_14?: number | null;
    bb_upper?: number | null;
    bb_middle?: number | null;
    bb_lower?: number | null;
    ma_20?: number | null;
    ma_50?: number | null;
    macd_cross?: string | null;
    macd_is_new_cross?: boolean;
    risk_reward_ratio?: number | null;
    market_status?: string | null;
    pe_percentile?: number | null;
    pb_percentile?: number | null;
    net_inflow?: number | null;
};
export type PortfolioCreate = components["schemas"]["PortfolioCreate"];
export interface AnalysisResponse {
    ticker: string;
    sentiment_score?: number;
    summary_status?: string;
    risk_level?: string;
    technical_analysis?: string;
    fundamental_news?: string;
    action_advice?: string;
    investment_horizon?: string;
    confidence_level?: number;
    immediate_action?: string;
    target_price?: number;
    stop_loss_price?: number;
    entry_zone?: string;
    rr_ratio?: string;
    is_cached?: boolean;
    model_used?: string;
    created_at?: string;
}
export type SearchResult = components["schemas"]["SearchResult"];
export interface UserProfile {
    id: string;
    email: string;
    membership_tier: string;
    has_gemini_key: boolean;
    has_deepseek_key: boolean;
    has_siliconflow_key: boolean;
    preferred_data_source: string;
    preferred_ai_model: string;
    timezone: string;
    theme: string;
    feishu_webhook_url?: string;
    enable_price_alerts: boolean;
    enable_hourly_summary: boolean;
    enable_daily_report: boolean;
    enable_macro_alerts: boolean;
}

export interface UserSettingsUpdate {
    api_key_gemini?: string;
    api_key_deepseek?: string;
    api_key_siliconflow?: string;
    preferred_data_source?: string;
    preferred_ai_model?: string;
    timezone?: string;
    theme?: string;
    feishu_webhook_url?: string;
    enable_price_alerts?: boolean;
    enable_hourly_summary?: boolean;
    enable_daily_report?: boolean;
    enable_macro_alerts?: boolean;
}
export interface SectorExposure {
    sector: string;
    weight: number;
    value: number;
}

export interface PortfolioSummary {
    total_market_value: number;
    total_unrealized_pl: number;
    total_pl_percent: number;
    day_change: number;
    holdings: PortfolioItem[];
    sector_exposure: SectorExposure[];
}

export interface PortfolioAnalysisResponse {
    health_score: number;
    risk_level: string;
    summary: string;
    diversification_analysis: string;
    strategic_advice: string;
    top_risks: string[];
    top_opportunities: string[];
    detailed_report: string;
    model_used?: string;
    created_at: string;
}

export interface GlobalNews {
    time: string;
    title: string;
    content: string;
}

export type TradeStatus = 'OPEN' | 'CLOSED_PROFIT' | 'CLOSED_LOSS' | 'CLOSED_MANUAL' | 'CLOSED_SYSTEM';

export interface SimulatedTrade {
    id: number;
    user_id: string;
    stock_ticker: string;
    entry_price: number;
    current_price: number;
    entry_date: string;
    exit_date?: string | null;
    status: TradeStatus;
    unrealized_pnl_pct: number;
    target_price?: number | null;
    stop_loss_price?: number | null;
    entry_reason?: string | null;
}
