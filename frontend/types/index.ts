import { components } from "./schema";

export type PortfolioItem = components["schemas"]["PortfolioItem"];
export type PortfolioCreate = components["schemas"]["PortfolioCreate"];
export interface AnalysisResponse {
    ticker: string;
    analysis: string;
    sentiment: string;
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
