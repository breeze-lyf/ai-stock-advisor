import api from "@/shared/api/client";

export { default } from "@/shared/api/client";

export type {
  AnalysisResponse,
  PasswordChange,
  PortfolioAnalysisResponse,
  PortfolioCreate,
  PortfolioItem,
  PortfolioSummary,
  SearchResult,
  TestConnectionRequest,
  TestConnectionResponse,
  UserProfile,
  UserSettingsUpdate,
  SimulatedTrade,
  TradeStatus,
} from "@/types";

export {
  analyzePortfolio,
  analyzeStock,
  getAnalysisHistory,
  getLatestAnalysis,
  getLatestPortfolioAnalysis,
  normalizeAnalysisResponse,
} from "@/features/analysis/api";
export {
  addPortfolioItem,
  deletePortfolioItem,
  fetchStockNews,
  getPortfolio,
  getPortfolioSummary,
  refreshStock,
  reorderPortfolio,
  searchStocks,
} from "@/features/portfolio/api";
export { changePassword, getProfile, testAIConnection, updateSettings } from "@/features/user/api";
export { getClsNews, getMacroRadar } from "@/features/macro/api";
export { fetchStockHistory, refreshAllStocks } from "@/features/market/api";
export {
  createSimulatedTrade,
  getSimulatedTrades,
  type CreateSimulatedTradeRequest,
} from "@/features/paper-trading/api";

export { api };
