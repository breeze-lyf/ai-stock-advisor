/**
 * API 客户端模块 (API Client Module)
 * 职责：基于 Axios 封装统一的 HTTP 请求，处理鉴权、错误拦截及响应解析
 */
import axios from "axios";
import {
    PortfolioItem,
    PortfolioCreate,
    AnalysisResponse,
    SearchResult,
    UserProfile,
    UserSettingsUpdate,
    PortfolioSummary,
    PortfolioAnalysisResponse
} from "@/types";

// 1. 基础配置 (Base Configuration)
const baseURL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/api$/, "");
const api = axios.create({
    baseURL,
    timeout: 180000,
    headers: {
        "Content-Type": "application/json",
    },
});

// 2. 请求拦截器 (Request Interceptor)
// 职责：在每个请求发出前，自动从 localStorage 注入 JWT Token
api.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// 3. 响应拦截器 (Response Interceptor)
// 职责：
//   - 网络错误 / 5xx 自动重试（最多 2 次，指数退避）
//   - 401/403 自动跳转登录页
const MAX_RETRIES = 2;

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error.config;

        // 认证错误：清理 token 并跳转登录
        if (error.response?.status === 401 || error.response?.status === 403) {
            if (typeof window !== "undefined") {
                localStorage.removeItem("token");
                if (!window.location.pathname.includes("/login")) {
                    window.location.href = "/login";
                }
            }
            return Promise.reject(error);
        }

        // 网络错误 或 5xx 服务端错误：自动重试
        const isRetryable =
            !error.response ||                     // 网络断开 (Network Error)
            (error.response.status >= 500 && error.response.status < 600);  // 5xx

        if (isRetryable && config && !config.__isRetry) {
            config.__retryCount = config.__retryCount || 0;
            if (config.__retryCount < MAX_RETRIES) {
                config.__retryCount += 1;
                config.__isRetry = true;

                // 指数退避：1s, 2s
                const delay = config.__retryCount * 1000;
                console.warn(
                    `[API Retry] ${config.method?.toUpperCase()} ${config.url} ` +
                    `attempt ${config.__retryCount}/${MAX_RETRIES} after ${delay}ms`
                );
                await new Promise((resolve) => setTimeout(resolve, delay));

                // 重置 __isRetry 以允许后续重试
                config.__isRetry = false;
                return api(config);
            }
        }

        return Promise.reject(error);
    }
);


export type {
    PortfolioItem,
    PortfolioCreate,
    AnalysisResponse,
    SearchResult,
    UserProfile,
    UserSettingsUpdate,
    PortfolioSummary,
    PortfolioAnalysisResponse
};

// --- 投资组合接口 (Portfolio API) ---

/** 获取用户持仓汇总数据 (含行业分布) */
export const getPortfolioSummary = async (): Promise<PortfolioSummary> => {
    const response = await api.get("/api/portfolio/summary");
    return response.data;
};

/** 获取用户持仓列表，refresh=true 时强制触发后端抓取，priceOnly=true 时仅同步价格 */
export const getPortfolio = async (refresh: boolean = false, priceOnly: boolean = false): Promise<PortfolioItem[]> => {
    const response = await api.get(`/api/portfolio/?refresh=${refresh}&price_only=${priceOnly}`);
    return response.data;
};

/** 添加股票到自选/持仓 */
export const addPortfolioItem = async (ticker: string, quantity: number, avg_cost: number) => {
    const response = await api.post("/api/portfolio/", { ticker, quantity, avg_cost });
    return response.data;
};

/** 从自选列表中删除股票 */
export const deletePortfolioItem = async (ticker: string) => {
    const response = await api.delete(`/api/portfolio/${ticker}`);
    return response.data;
};

/** 单个股票行情强制刷新 (支持 priceOnly) */
export const refreshStock = async (ticker: string, priceOnly: boolean = false): Promise<Partial<PortfolioItem>> => {
    const response = await api.post(`/api/portfolio/${ticker}/refresh?price_only=${priceOnly}`);
    return response.data;
};

/** 搜索股票：remote=true 时会从外部源 (yfinance/akshare) 实时搜索并入库 */
export const searchStocks = async (query: string, remote: boolean = false): Promise<SearchResult[]> => {
    const response = await api.get(`/api/portfolio/search?query=${query}&remote=${remote}`);
    return response.data;
};

// --- AI 分析接口 (AI Analysis API) ---

/** 发起 AI 分析任务（force=true 会跳过缓存重新生成） */
export const analyzeStock = async (ticker: string, force: boolean = false): Promise<AnalysisResponse> => {
    const response = await api.post(`/api/analysis/${ticker}?force=${force}`);
    return response.data;
};

/** 获取该股票最新的 AI 分析缓存 */
export const getLatestAnalysis = async (ticker: string): Promise<AnalysisResponse | null> => {
    try {
        const response = await api.get(`/api/analysis/${ticker}`);
        return response.data;
    } catch (error: any) {
        if (error.response?.status === 404) {
            return null; // 404 表示尚未有分析记录，属于合法业务状态
        }
        throw error;
    }
};

/** 发起全量持仓 AI 诊断 */
export const analyzePortfolio = async (): Promise<PortfolioAnalysisResponse> => {
    const response = await api.post("/api/analysis/portfolio");
    return response.data;
};

/** 获取单个股票的 AI 分析历史记录 */
export const getAnalysisHistory = async (ticker: string): Promise<AnalysisResponse[]> => {
    const response = await api.get(`/api/analysis/${ticker}/history`);
    return response.data;
};

/** 获取最新的全量持仓诊断缓存 */
export const getLatestPortfolioAnalysis = async (): Promise<PortfolioAnalysisResponse | null> => {
    try {
        const response = await api.get("/api/analysis/portfolio");
        return response.data;
    } catch (error: any) {
        if (error.response?.status === 404) {
            return null;
        }
        throw error;
    }
};

/** 批量重排自选股 */
export const reorderPortfolio = async (orders: { ticker: string; sort_order: number }[]): Promise<{ message: string }> => {
    const response = await api.patch("/api/portfolio/reorder", orders);
    return response.data;
};

// --- 用户与设置接口 (User & Settings API) ---

/** 获取个人资料 */
export const getProfile = async (): Promise<UserProfile> => {
    const response = await api.get("/api/user/me");
    return response.data;
};

/** 更新用户配置（如偏好模型、数据源等） */
export const updateSettings = async (settings: UserSettingsUpdate): Promise<UserProfile> => {
    const response = await api.put("/api/user/settings", settings);
    return response.data;
};

export interface PasswordChange {
    old_password: string;
    new_password: string;
}

/** 修改密码 */
export const changePassword = async (data: PasswordChange) => {
    const response = await api.put("/api/user/password", data);
    return response.data;
};

// --- 市场数据接口 (Market Data API) ---

/** 从数据库获取股票新闻管道列表 */
export const fetchStockNews = async (ticker: string) => {
    const response = await api.get(`/api/portfolio/${ticker}/news`);
    return response.data;
};

/** 获取历史 K 线数据（用于 ECharts/LightweightChart 渲染） */
export const fetchStockHistory = async (ticker: string, period: string = "1y") => {
    const response = await api.get(`/api/stocks/${ticker}/history?period=${period}`);
    return response.data;
};

/** 强制刷新所有持仓股票数据 (支持 priceOnly) */
export const refreshAllStocks = async (priceOnly: boolean = false): Promise<{ message: string, updated_count: number }> => {
    const response = await api.post(`/api/stocks/refresh_all?price_only=${priceOnly}`);
    return response.data;
};

/** 全球宏观热点雷达接口 (Global Macro Radar) */
export const getMacroRadar = async (refresh: boolean = false): Promise<any[]> => {
    const response = await api.get(`/api/macro/radar?refresh=${refresh}`);
    return response.data;
};

/** 获取财联社全球电报资讯 */
export const getClsNews = async (refresh: boolean = false): Promise<any[]> => {
    const response = await api.get(`/api/macro/cls_news?refresh=${refresh}`);
    return response.data;
};

import { SimulatedTrade, TradeStatus } from "@/types";

/**
 * 纸交易 (Paper Trading) / 远航模拟舱 接口
 */
export const getSimulatedTrades = async (status?: TradeStatus): Promise<SimulatedTrade[]> => {
    const query = status ? `?status=${status}` : "";
    const response = await api.get(`/api/paper-trading${query}`);
    return response.data;
};

export interface CreateSimulatedTradeRequest {
    ticker: string;
    entry_price: number;
    entry_reason: string;
    target_price?: number;
    stop_loss_price?: number;
}

export const createSimulatedTrade = async (params: CreateSimulatedTradeRequest): Promise<{ message: string, trade_id: number }> => {
    // Note: The FastAPI endpoint expects query parameters for POST in this particular implementation snippet, but it's better to verify. Wait, FastAPI `create_simulated_trade(ticker: str, entry_price: float...)` without Pydantic model usually means query parameters. 
    // Let's pass them as query params as defined in the router.
    const urlParams = new URLSearchParams();
    urlParams.append("ticker", params.ticker);
    urlParams.append("entry_price", params.entry_price.toString());
    urlParams.append("entry_reason", params.entry_reason);
    if (params.target_price) urlParams.append("target_price", params.target_price.toString());
    if (params.stop_loss_price) urlParams.append("stop_loss_price", params.stop_loss_price.toString());
    
    const response = await api.post(`/api/paper-trading/?${urlParams.toString()}`);
    return response.data;
};

export default api;
