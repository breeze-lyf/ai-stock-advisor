import { components } from "./schema";

export type PortfolioItem = components["schemas"]["PortfolioItem"] & {
    macd_cross?: string | null;
    macd_is_new_cross?: boolean;
    risk_reward_ratio?: number | null;
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
}

export interface UserSettingsUpdate {
    api_key_gemini?: string;
    api_key_deepseek?: string;
    api_key_siliconflow?: string;
    preferred_data_source?: string;
    preferred_ai_model?: string;
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
