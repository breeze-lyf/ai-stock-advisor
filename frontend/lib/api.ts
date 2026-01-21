import axios from "axios";

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
    headers: {
        "Content-Type": "application/json",
    },
});

api.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

export interface PortfolioItem {
    ticker: string;
    quantity: number;
    avg_cost: number;
    current_price: number;
    market_value: number;
    unrealized_pl: number;
    pl_percent: number;
    last_updated?: string;

    // Fundamental fields
    sector?: string;
    industry?: string;
    market_cap?: number;
    pe_ratio?: number;
    forward_pe?: number;
    eps?: number;
    dividend_yield?: number;
    beta?: number;
    fifty_two_week_high?: number;
    fifty_two_week_low?: number;

    // Technical indicator fields
    rsi_14?: number;
    ma_20?: number;
    ma_50?: number;
    ma_200?: number;
    macd_val?: number;
    macd_signal?: number;
    macd_hist?: number;
    bb_upper?: number;
    bb_middle?: number;
    bb_lower?: number;
    atr_14?: number;
    k_line?: number;
    d_line?: number;
    j_line?: number;
    volume_ma_20?: number;
    volume_ratio?: number;
    change_percent?: number;
}

export interface PortfolioCreate {
    ticker: string;
    quantity: number;
    avg_cost: number;
}

export interface AnalysisResponse {
    ticker: string;
    analysis: string;
    sentiment: "BULLISH" | "BEARISH" | "NEUTRAL";
}

export const getPortfolio = async (refresh: boolean = false): Promise<PortfolioItem[]> => {
    const response = await api.get(`/api/portfolio/?refresh=${refresh}`);
    return response.data;
};

export const addPortfolioItem = async (ticker: string, quantity: number, avg_cost: number) => {
    const response = await api.post("/api/portfolio/", { ticker, quantity, avg_cost });
    return response.data;
};

export const deletePortfolioItem = async (ticker: string) => {
    const response = await api.delete(`/api/portfolio/${ticker}`);
    return response.data;
};

export interface SearchResult {
    ticker: string;
    name: string;
}

export const searchStocks = async (query: string, remote: boolean = false): Promise<SearchResult[]> => {
    const response = await api.get(`/api/portfolio/search?query=${query}&remote=${remote}`);
    return response.data;
};

export const analyzeStock = async (ticker: string): Promise<AnalysisResponse> => {
    const response = await api.post(`/api/analysis/${ticker}`);
    return response.data;
};

export interface UserProfile {
    id: string;
    email: string;
    membership_tier: string;
    has_gemini_key: boolean;
    has_deepseek_key: boolean;
    preferred_data_source: "ALPHA_VANTAGE" | "YFINANCE";
}

export interface UserSettingsUpdate {
    api_key_gemini?: string;
    api_key_deepseek?: string;
    preferred_data_source?: "ALPHA_VANTAGE" | "YFINANCE";
}

export const getProfile = async (): Promise<UserProfile> => {
    const response = await api.get("/api/user/me");
    return response.data;
};

export const updateSettings = async (settings: UserSettingsUpdate): Promise<UserProfile> => {
    const response = await api.put("/api/user/settings", settings);
    return response.data;
};

export default api;
