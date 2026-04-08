import api from "@/shared/api/client";

export interface StockScreenerResult {
    ticker: string;
    name: string;
    current_price: number;
    pe_ratio?: number;
    pb_ratio?: number;
    roe?: number;
    revenue_growth?: number;
    earnings_growth?: number;
    dividend_yield?: number;
    market_cap?: number;
    sector?: string;
    industry?: string;
    rsi_14?: number;
    macd_golden_cross?: boolean;
    above_ma20?: boolean;
    above_ma50?: boolean;
}

export interface PresetStrategyResponse {
    strategy: string;
    count: number;
    stocks: StockScreenerResult[];
}

export interface CustomScreenerResponse {
    filters: Record<string, unknown>;
    count: number;
    stocks: StockScreenerResult[];
}

export interface TechnicalScreenerResponse {
    filters: {
        rsi_min?: number;
        rsi_max?: number;
        macd_golden_cross: boolean;
        above_ma20: boolean;
        above_ma50: boolean;
    };
    count: number;
    stocks: StockScreenerResult[];
}

export async function getPresetStrategy(
    strategy: "low_valuation" | "growth" | "momentum" | "high_dividend",
    limit = 50
): Promise<PresetStrategyResponse> {
    const response = await api.get(`/api/v1/screener/presets`, {
        params: { strategy, limit },
    });
    return response.data;
}

export async function screenCustom(
    filters: {
        pe_ratio_min?: number;
        pe_ratio_max?: number;
        pb_ratio_min?: number;
        pb_ratio_max?: number;
        roe_min?: number;
        revenue_growth_min?: number;
        earnings_growth_min?: number;
        dividend_yield_min?: number;
        market_cap_min?: number;
        market_cap_max?: number;
        sector?: string;
        exchange?: string;
    },
    limit = 50
): Promise<CustomScreenerResponse> {
    const response = await api.get(`/api/v1/screener/custom`, {
        params: { ...filters, limit },
    });
    return response.data;
}

export async function screenTechnical(
    filters: {
        rsi_min?: number;
        rsi_max?: number;
        macd_golden_cross?: boolean;
        above_ma20?: boolean;
        above_ma50?: boolean;
    },
    limit = 50
): Promise<TechnicalScreenerResponse> {
    const response = await api.get(`/api/v1/screener/technical`, {
        params: { ...filters, limit },
    });
    return response.data;
}

export async function getSectors(): Promise<{ sectors: string[] }> {
    const response = await api.get(`/api/v1/screener/sectors`);
    return response.data;
}

export async function getIndustries(): Promise<{ industries: string[] }> {
    const response = await api.get(`/api/v1/screener/industries`);
    return response.data;
}
