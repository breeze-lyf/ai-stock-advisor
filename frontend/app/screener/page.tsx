"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { getPresetStrategy, screenCustom, screenTechnical, getSectors, getIndustries, type StockScreenerResult } from "@/features/screener/api";
import { Search, Filter, Star, Zap, TrendingUp, PieChart, Activity, DollarSign, BarChart3 } from "lucide-react";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import { SearchDialog } from "@/components/features/SearchDialog";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";

type TabType = "preset" | "fundamental" | "technical";
type PresetStrategy = "low_valuation" | "growth" | "momentum" | "high_dividend";

const PRESET_STRATEGIES = [
    { value: "low_valuation" as PresetStrategy, label: "低估值", description: "PE<15, PB<2, 股息率>2%", icon: Star, color: "blue" },
    { value: "growth" as PresetStrategy, label: "成长股", description: "营收增速>20%, ROE>15%", icon: TrendingUp, color: "emerald" },
    { value: "momentum" as PresetStrategy, label: "动量", description: "RSI>50, MACD 金叉", icon: Zap, color: "amber" },
    { value: "high_dividend" as PresetStrategy, label: "高股息", description: "股息率>5%, PE<20", icon: PieChart, color: "purple" },
] as const;

export default function ScreenerPage() {
    const { isAuthenticated, user } = useAuth();
    const { portfolio, user: userProfile } = useDashboardPortfolioData(isAuthenticated);
    const [activeTab, setActiveTab] = useState<TabType>("preset");
    const [selectedStrategy, setSelectedStrategy] = useState<PresetStrategy>("low_valuation");
    const [screenerResults, setScreenerResults] = useState<StockScreenerResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [sectors, setSectors] = useState<string[]>([]);
    const [industries, setIndustries] = useState<string[]>([]);
    const [resultCount, setResultCount] = useState(0);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [activeHeaderTab, setActiveHeaderTab] = useState<DashboardTab>("analysis");

    const [fundamentalFilters, setFundamentalFilters] = useState({
        pe_ratio_min: "",
        pe_ratio_max: "",
        pb_ratio_min: "",
        pb_ratio_max: "",
        roe_min: "",
        revenue_growth_min: "",
        earnings_growth_min: "",
        dividend_yield_min: "",
        market_cap_min: "",
        market_cap_max: "",
        sector: "",
    });

    const [technicalFilters, setTechnicalFilters] = useState({
        rsi_min: "",
        rsi_max: "",
        macd_golden_cross: false,
        above_ma20: false,
        above_ma50: false,
    });

    useEffect(() => {
        const loadData = async () => {
            try {
                const [sectorsData, industriesData] = await Promise.all([getSectors(), getIndustries()]);
                setSectors(sectorsData.sectors || []);
                setIndustries(industriesData.industries || []);
            } catch (error) {
                console.error("Failed to load sectors/industries:", error);
            }
        };
        loadData();
    }, []);

    useEffect(() => {
        if (activeTab === "preset") {
            handleRunPreset(selectedStrategy);
        }
    }, [activeTab]);

    const handleRunPreset = async (strategy: PresetStrategy) => {
        setLoading(true);
        try {
            const result = await getPresetStrategy(strategy, 100);
            setScreenerResults(result.stocks);
            setResultCount(result.count);
        } catch (error) {
            console.error("Failed to run preset strategy:", error);
            setScreenerResults([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleRunFundamental = async () => {
        setLoading(true);
        try {
            const filters: Record<string, number | string> = {};
            Object.entries(fundamentalFilters).forEach(([key, value]) => {
                if (value !== "" && value !== "0") {
                    filters[key] = Number(value);
                }
            });
            const result = await screenCustom(filters, 100);
            setScreenerResults(result.stocks);
            setResultCount(result.count);
        } catch (error) {
            console.error("Failed to run fundamental screener:", error);
            setScreenerResults([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleRunTechnical = async () => {
        setLoading(true);
        try {
            const filters: Record<string, number | boolean> = {};
            if (technicalFilters.rsi_min !== "") filters.rsi_min = Number(technicalFilters.rsi_min);
            if (technicalFilters.rsi_max !== "") filters.rsi_max = Number(technicalFilters.rsi_max);
            if (technicalFilters.macd_golden_cross) filters.macd_golden_cross = true;
            if (technicalFilters.above_ma20) filters.above_ma20 = true;
            if (technicalFilters.above_ma50) filters.above_ma50 = true;
            const result = await screenTechnical(filters, 100);
            setScreenerResults(result.stocks);
            setResultCount(result.count);
        } catch (error) {
            console.error("Failed to run technical screener:", error);
            setScreenerResults([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
            <DashboardHeader user={userProfile} activeTab={activeHeaderTab} setActiveTab={setActiveHeaderTab} />
            <SearchDialog
                isOpen={isSearchOpen}
                onOpenChange={setIsSearchOpen}
                onRefresh={() => {}}
                onSelectTicker={() => {}}
                portfolio={portfolio}
            />
            <main className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                <div className="p-6 space-y-6">
                {/* Page Header */}
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-linear-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <Search className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white">选股器</h1>
                        <p className="text-xs text-slate-500 dark:text-slate-400">基本面 · 技术面 · 预设策略</p>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-2">
                    <TabButton active={activeTab === "preset"} onClick={() => setActiveTab("preset")} icon={<Star className="w-4 h-4" />} label="预设策略" />
                    <TabButton active={activeTab === "fundamental"} onClick={() => setActiveTab("fundamental")} icon={<DollarSign className="w-4 h-4" />} label="基本面选股" />
                    <TabButton active={activeTab === "technical"} onClick={() => setActiveTab("technical")} icon={<Activity className="w-4 h-4" />} label="技术面选股" />
                </div>

                {/* Preset Strategies */}
                {activeTab === "preset" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {PRESET_STRATEGIES.map((strategy) => {
                            const Icon = strategy.icon;
                            return (
                                <button
                                    key={strategy.value}
                                    onClick={() => {
                                        setSelectedStrategy(strategy.value);
                                        handleRunPreset(strategy.value);
                                    }}
                                    type="button"
                                    className={`p-4 rounded-xl border text-left transition-all ${
                                        selectedStrategy === strategy.value
                                            ? "bg-blue-600 text-white border-blue-600 shadow-lg shadow-blue-500/20"
                                            : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-blue-300"
                                    }`}
                                >
                                    <div className="flex items-center gap-3 mb-2">
                                        <Icon className={`w-5 h-5 ${selectedStrategy === strategy.value ? "text-white" : "text-blue-600"}`} />
                                        <span className="font-bold text-sm">{strategy.label}</span>
                                    </div>
                                    <p className={`text-xs ${selectedStrategy === strategy.value ? "text-blue-100" : "text-slate-500"}`}>{strategy.description}</p>
                                </button>
                            );
                        })}
                    </div>
                )}

                {/* Fundamental Filters */}
                {activeTab === "fundamental" && (
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            <FilterInput label="PE (最小)" value={fundamentalFilters.pe_ratio_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pe_ratio_min: v })} />
                            <FilterInput label="PE (最大)" value={fundamentalFilters.pe_ratio_max} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pe_ratio_max: v })} />
                            <FilterInput label="PB (最小)" value={fundamentalFilters.pb_ratio_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pb_ratio_min: v })} />
                            <FilterInput label="PB (最大)" value={fundamentalFilters.pb_ratio_max} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pb_ratio_max: v })} />
                            <FilterInput label="ROE (最小)%" value={fundamentalFilters.roe_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, roe_min: v })} />
                            <FilterInput label="营收增速 (最小)%" value={fundamentalFilters.revenue_growth_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, revenue_growth_min: v })} />
                            <FilterInput label="净利润增速 (最小)%" value={fundamentalFilters.earnings_growth_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, earnings_growth_min: v })} />
                            <FilterInput label="股息率 (最小)%" value={fundamentalFilters.dividend_yield_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, dividend_yield_min: v })} />
                        </div>
                        <div className="flex gap-2 pt-4">
                            <button onClick={handleRunFundamental} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-bold" type="button">
                                开始选股
                            </button>
                        </div>
                    </div>
                )}

                {/* Technical Filters */}
                {activeTab === "technical" && (
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            <FilterInput label="RSI (最小)" value={technicalFilters.rsi_min} onChange={(v) => setTechnicalFilters({ ...technicalFilters, rsi_min: v })} />
                            <FilterInput label="RSI (最大)" value={technicalFilters.rsi_max} onChange={(v) => setTechnicalFilters({ ...technicalFilters, rsi_max: v })} />
                            <FilterCheckbox label="MACD 金叉" checked={technicalFilters.macd_golden_cross} onChange={(v) => setTechnicalFilters({ ...technicalFilters, macd_golden_cross: v })} />
                            <FilterCheckbox label="站上 20 日线" checked={technicalFilters.above_ma20} onChange={(v) => setTechnicalFilters({ ...technicalFilters, above_ma20: v })} />
                            <FilterCheckbox label="站上 50 日线" checked={technicalFilters.above_ma50} onChange={(v) => setTechnicalFilters({ ...technicalFilters, above_ma50: v })} />
                        </div>
                        <div className="flex gap-2 pt-4">
                            <button onClick={handleRunTechnical} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-bold" type="button">
                                开始选股
                            </button>
                        </div>
                    </div>
                )}

                {/* Results */}
                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                        <span className="ml-3 text-slate-500">筛选中...</span>
                    </div>
                )}

                {!loading && screenerResults.length > 0 && (
                    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">筛选结果</span>
                            <span className="text-xs text-slate-500">{resultCount} 只股票</span>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-slate-50 dark:bg-slate-900">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">代码</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">名称</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">价格</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">涨跌幅%</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">PE</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">PB</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">ROE%</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">RSI</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                    {screenerResults.map((stock) => (
                                        <tr key={stock.ticker} className="hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                                            <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">{stock.ticker}</td>
                                            <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{stock.name}</td>
                                            <td className="px-4 py-3 text-sm text-right text-slate-900 dark:text-white">${stock.current_price?.toFixed(2) || "--"}</td>
                                            <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">{stock.pe_ratio?.toFixed(2) || "--"}</td>
                                            <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">{stock.pb_ratio?.toFixed(2) || "--"}</td>
                                            <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">{stock.roe?.toFixed(2) || "--"}</td>
                                            <td className="px-4 py-3 text-sm text-right text-slate-600 dark:text-slate-300">{stock.rsi_14?.toFixed(2) || "--"}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {!loading && screenerResults.length === 0 && (
                    <div className="text-center py-12 text-slate-400">
                        <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p className="text-sm">暂无筛选结果</p>
                    </div>
                )}
                </div>
            </main>
        </div>
    );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
    return (
        <button onClick={onClick} type="button" className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            active
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-blue-300"
        }`}>
            {icon}
            {label}
        </button>
    );
}

function FilterInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
    return (
        <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={label}
                aria-label={label}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm text-slate-900 dark:text-white"
            />
        </div>
    );
}

function FilterCheckbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
    return (
        <div className="flex items-center gap-2 pt-6">
            <input
                type="checkbox"
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                aria-label={label}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</label>
        </div>
    );
}
