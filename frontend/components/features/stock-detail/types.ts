/**
 * 股票详情页子组件的类型定义 (Sub-component Type Definitions)
 * 职责：为所有拆分后的子组件提供严格的 Props 接口契约
 */
import { PortfolioItem } from "@/types";

// ========================================
// AI 数据接口 (从 StockDetail Props 提取)
// ========================================

/** AI 分析结果的完整数据结构 */
export interface AIData {
    ticker?: string;
    sentiment_score?: number;
    summary_status?: string;
    risk_level?: string;
    technical_analysis?: string;
    fundamental_news?: string;
    news_summary?: string;
    fundamental_analysis?: string;
    macro_risk_note?: string;
    action_advice?: string;
    immediate_action?: string;
    target_price?: number;
    stop_loss_price?: number;
    entry_zone?: string;
    entry_price_low?: number;
    entry_price_high?: number;
    rr_ratio?: string;
    investment_horizon?: string;
    confidence_level?: number;
    thought_process?: Array<{ step: string; content: string }>;
    is_cached?: boolean;
    created_at?: string;
    model_used?: string;
}

// ========================================
// 各板块 Props 接口
// ========================================

/** 粘性顶栏 Props */
export interface StickyBarProps {
    selectedItem: PortfolioItem;
    isScrolled: boolean;
    refreshing: boolean;
    onRefresh: () => void;
    onBack?: () => void;
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
}

/** 股票身份头 Props */
export interface HeaderIdentityProps {
    selectedItem: PortfolioItem;
    isScrolled: boolean;
    refreshing: boolean;
    onRefresh: () => void;
    onBack?: () => void;
}

/** 动态行情分析 Props */
export interface MarketAnalysisProps {
    historyData: any[];
    ticker: string;
    showBb: boolean;
    showRsi: boolean;
    showMacd: boolean;
    onToggleBb: () => void;
    onToggleRsi: () => void;
    onToggleMacd: () => void;
}

/** AI 智能判研指标 Props */
export interface AIVerdictProps {
    selectedItem: PortfolioItem;
    aiData: AIData | null;
    analysisHistory: any[];
    analyzing: boolean;
    onAnalyze: (force?: boolean) => void;
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
}

/** 技术面深度透视 Props */
export interface TechnicalInsightsProps {
    selectedItem: PortfolioItem;
    aiData: AIData | null;
    analyzing: boolean;
}

/** 基本面资料卡 Props */
export interface FundamentalCardProps {
    selectedItem: PortfolioItem;
    aiData: AIData | null;
}

/** 实时资讯流 Props */
export interface NewsFeedProps {
    news: any[];
}
