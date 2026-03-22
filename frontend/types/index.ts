import { components } from "./schema";

export type PortfolioItem = components["schemas"]["PortfolioItem"] & {
    price?: number | null;
    weight?: number | null;
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
    decision_mode?: string;
    dominant_driver?: string;
    trade_setup_status?: string;
    sentiment_score?: number;
    summary_status?: string;
    core_logic_summary?: string;
    risk_level?: string;
    trigger_condition?: string;
    invalidation_condition?: string;
    next_review_point?: string;
    technical_analysis?: string;
    fundamental_news?: string;
    news_summary?: string;
    fundamental_analysis?: string;
    macro_risk_note?: string;
    add_on_trigger?: string;
    action_advice?: string;
    investment_horizon?: string;
    confidence_level?: number;
    immediate_action?: string;
    target_price?: number;
    target_price_1?: number;
    target_price_2?: number;
    stop_loss_price?: number;
    max_position_pct?: number;
    entry_zone?: string;
    entry_price_low?: number;
    entry_price_high?: number;
    rr_ratio?: string;
    bull_case?: string;
    base_case?: string;
    bear_case?: string;
    is_cached?: boolean;
    model_used?: string;
    created_at?: string;
}
export type SearchResult = components["schemas"]["SearchResult"];
export type ApiConfig = components["schemas"]["ApiConfig"];
export type UserProviderCredentialInput = {
    api_key?: string | null;
    base_url?: string | null;
    is_enabled?: boolean | null;
};
export type UserProviderCredentialResponse = {
    has_key: boolean;
    base_url?: string | null;
    is_enabled: boolean;
};
export type UserProfile = components["schemas"]["UserProfile"] & {
    notifications_enabled?: boolean;
    provider_credentials?: Record<string, UserProviderCredentialResponse> | null;
};
export type UserSettingsUpdate = components["schemas"]["UserSettingsUpdate"] & {
    notifications_enabled?: boolean;
    provider_credentials?: Record<string, UserProviderCredentialInput> | null;
};
export type PasswordChange = components["schemas"]["PasswordChange"];
export type TestConnectionRequest = components["schemas"]["TestConnectionRequest"];
export type TestConnectionResponse = components["schemas"]["TestConnectionResponse"];

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
