import axios from "axios";
import {
    PortfolioItem,
    PortfolioCreate,
    AnalysisResponse,
    SearchResult,
    UserProfile,
    UserSettingsUpdate
} from "@/types";

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

export type {
    PortfolioItem,
    PortfolioCreate,
    AnalysisResponse,
    SearchResult,
    UserProfile,
    UserSettingsUpdate
};

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

export const refreshStock = async (ticker: string): Promise<Partial<PortfolioItem>> => {
    const response = await api.post(`/api/portfolio/${ticker}/refresh`);
    return response.data;
};


export const searchStocks = async (query: string, remote: boolean = false): Promise<SearchResult[]> => {
    const response = await api.get(`/api/portfolio/search?query=${query}&remote=${remote}`);
    return response.data;
};

export const analyzeStock = async (ticker: string): Promise<AnalysisResponse> => {
    const response = await api.post(`/api/analysis/${ticker}`);
    return response.data;
};



export const getProfile = async (): Promise<UserProfile> => {
    const response = await api.get("/api/user/me");
    return response.data;
};

export const updateSettings = async (settings: UserSettingsUpdate): Promise<UserProfile> => {
    const response = await api.put("/api/user/settings", settings);
    return response.data;
};

export default api;
