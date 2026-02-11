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
    UserSettingsUpdate
} from "@/types";

// 1. 基础配置 (Base Configuration)
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
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
    UserSettingsUpdate
};

// --- 投资组合接口 (Portfolio API) ---

/** 获取用户持仓列表，refresh=true 时强制触发后端抓取最新行情 */
export const getPortfolio = async (refresh: boolean = false): Promise<PortfolioItem[]> => {
    const response = await api.get(`/api/portfolio/?refresh=${refresh}`);
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

/** 单个股票行情强制刷新 */
export const refreshStock = async (ticker: string): Promise<Partial<PortfolioItem>> => {
    const response = await api.post(`/api/portfolio/${ticker}/refresh`);
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
export const getLatestAnalysis = async (ticker: string): Promise<AnalysisResponse> => {
    const response = await api.get(`/api/analysis/${ticker}`);
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

export default api;
