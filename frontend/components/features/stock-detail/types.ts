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
    decision_mode?: string;
    dominant_driver?: string;
    trade_setup_status?: string;
    sentiment_score?: number;
    core_logic_summary?: string;
    summary_status?: string;
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
    investment_horizon?: string;
    confidence_level?: number;
    confidence_breakdown?: {
        technical?: number;
        fundamental?: number;
        macro?: number;
        sentiment?: number;
    };
    key_assumptions?: Array<{ assumption: string; breakpoint: string }>;
    catalysts?: Array<{ date: string; event: string; type: string; impact: string; description: string }>;
    thought_process?: Array<{ step: string; content: string }>;
    scenario_tags?: Array<{ category: string; value: string }>;
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
    activeTab?: "info" | "analysis";
    onTabChange?: (tab: "info" | "analysis") => void;
}

/** 股票身份头 Props */
export interface HeaderIdentityProps {
    selectedItem: PortfolioItem;
    isScrolled: boolean;
    refreshing: boolean;
    onRefresh: () => void;
    onBack?: () => void;
    activeTab?: "info" | "analysis";
    onTabChange?: (tab: "info" | "analysis") => void;
}

/** 历史数据项类型 */
export interface HistoryDataItem {
    time: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
    [key: string]: unknown;
}

/** 分析历史项类型 */
export interface AnalysisHistoryItem {
    id?: string;
    created_at?: string;
    immediate_action?: string;
    history_price?: number;
    risk_level?: string;
    confidence_level?: number | string;
    [key: string]: unknown;
}

/** 新闻项类型 */
export interface NewsItem {
    title?: string;
    url?: string;
    published_at?: string;
    source?: string;
    [key: string]: unknown;
}

/** 动态行情分析 Props */
export interface MarketAnalysisProps {
    historyData: HistoryDataItem[];
    ticker: string;
    showBb: boolean;
    showRsi: boolean;
    showMacd: boolean;
    onToggleBb: () => void;
    onToggleRsi: () => void;
    onToggleMacd: () => void;
    onLoadMore?: (earliestTime: string) => void;
    isLoadingMore?: boolean;
    isLoading?: boolean;
}

/** AI 智能判研指标 Props */
export interface AIVerdictProps {
    selectedItem: PortfolioItem;
    aiData: AIData | null;
    analysisHistory: AnalysisHistoryItem[];
    analyzing: boolean;
    onAnalyze: (force?: boolean) => void;
    currency: string;
    sanitizePrice: (val: number | null | undefined) => string;
}

/** 技术面深度透视 Props */
export interface TechnicalInsightsProps {
    selectedItem: PortfolioItem;
    /** Pre-computed AI technical digest (from stock_capsules table) */
    technicalCapsule?: string | null;
    technicalCapsuleUpdatedAt?: string | null;
    onRefreshCapsule?: () => void;
    refreshingCapsule?: boolean;
}

/** 基本面资料卡 Props */
export interface FundamentalCardProps {
    selectedItem: PortfolioItem;
    /** Pre-computed AI fundamental digest (from stock_capsules table) */
    fundamentalCapsule?: string | null;
    fundamentalCapsuleUpdatedAt?: string | null;
    onRefreshCapsule?: () => void;
    refreshingCapsule?: boolean;
}

/** 实时资讯流 Props */
export interface NewsFeedProps {
    news: NewsItem[];
    /** Pre-computed AI news digest (from stock_capsules table) */
    newsCapsule?: string | null;
    newsCapsuleUpdatedAt?: string | null;
    onRefreshCapsule?: () => void;
    refreshingCapsule?: boolean;
}
