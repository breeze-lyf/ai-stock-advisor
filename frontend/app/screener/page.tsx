"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getPresetStrategy, screenCustom, screenTechnical, getSectors, getIndustries, type StockScreenerResult } from "@/features/screener/api";
import { Search, Filter, Star, Zap, TrendingUp, PieChart, Activity, DollarSign, BarChart3, ArrowLeft } from "lucide-react";

type TabType = "preset" | "fundamental" | "technical";
type PresetStrategy = "low_valuation" | "growth" | "momentum" | "high_dividend";

const PRESET_STRATEGIES = [
    { value: "low_valuation" as PresetStrategy, label: "低估值", description: "PE<15, PB<2, 股息率>2%", icon: Star, color: "blue" },
    { value: "growth" as PresetStrategy, label: "成长股", description: "营收增速>20%, ROE>15%", icon: TrendingUp, color: "emerald" },
    { value: "momentum" as PresetStrategy, label: "动量", description: "RSI>50, MACD 金叉", icon: Zap, color: "amber" },
    { value: "high_dividend" as PresetStrategy, label: "高股息", description: "股息率>5%, PE<20", icon: PieChart, color: "purple" },
] as const;

export default function ScreenerPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<TabType>("preset");
    const [selectedStrategy, setSelectedStrategy] = useState<PresetStrategy>("low_valuation");
    const [screenerResults, setScreenerResults] = useState<StockScreenerResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [sectors, setSectors] = useState<string[]>([]);
    const [industries, setIndustries] = useState<string[]>([]);
    const [resultCount, setResultCount] = useState(0);

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
            Object.entries(technicalFilters).forEach(([key, value]) => {
                if (value !== "" && value !== "0") {
                    filters[key] = typeof value === "string" ? Number(value) : value;
                }
            });
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

    const handleBack = () => {
        router.push("/");
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
            {/* Top Bar with Back Button */}
            <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3">
                <div className="flex items-center gap-4">
                    <button
                        onClick={handleBack}
                        type="button"
                        className="flex items-center gap-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        <span className="text-sm font-medium">返回</span>
                    </button>
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-linear-to-br from-blue-600 to-blue-700 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <span className="text-white font-bold text-sm">A</span>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white">选股器</h1>
                            <p className="text-xs text-slate-500 dark:text-slate-400">预设策略 · 基本面 · 技术面</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="p-6">
                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    <TabButton active={activeTab === "preset"} onClick={() => setActiveTab("preset")} icon={<Star />} label="预设策略" />
                    <TabButton active={activeTab === "fundamental"} onClick={() => setActiveTab("fundamental")} icon={<Filter />} label="基本面" />
                    <TabButton active={activeTab === "technical"} onClick={() => setActiveTab("technical")} icon={<Activity />} label="技术面" />
                </div>

                {/* Preset Strategies */}
                {activeTab === "preset" && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            {PRESET_STRATEGIES.map(({ value, label, description, icon: Icon, color }) => (
                                <button
                                    key={value}
                                    type="button"
                                    onClick={() => { setSelectedStrategy(value); handleRunPreset(value); }}
                                    className={`p-4 rounded-xl border text-left transition-all ${
                                        selectedStrategy === value
                                            ? `border-${color}-600 bg-${color}-50 dark:bg-${color}-900/20`
                                            : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-blue-300"
                                    }`}
                                >
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className={`p-2 rounded-lg ${selectedStrategy === value ? `bg-${color}-600` : "bg-slate-100 dark:bg-slate-700"}`}>
                                            <Icon className={`h-5 w-5 ${selectedStrategy === value ? "text-white" : "text-slate-600 dark:text-slate-300"}`} />
                                        </div>
                                        <span className="font-semibold text-slate-900 dark:text-white">{label}</span>
                                    </div>
                                    <p className="text-xs text-slate-500">{description}</p>
                                </button>
                            ))}
                        </div>

                        {loading && (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                <span className="ml-3 text-slate-500">运行策略中...</span>
                            </div>
                        )}

                        {!loading && screenerResults.length > 0 && (
                            <ResultsTable stocks={screenerResults} count={resultCount} />
                        )}

                        {!loading && screenerResults.length === 0 && resultCount === 0 && (
                            <div className="text-center py-12 text-slate-400">
                                <Search className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                <p className="text-sm">点击策略卡片开始筛选</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Fundamental Filters */}
                {activeTab === "fundamental" && (
                    <div className="space-y-6">
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <DollarSign className="h-5 w-5 text-slate-400" />
                                基本面筛选条件
                            </h3>
                            <div className="grid md:grid-cols-3 gap-4">
                                <FilterInput label="PE 最小值" value={fundamentalFilters.pe_ratio_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pe_ratio_min: v })} />
                                <FilterInput label="PE 最大值" value={fundamentalFilters.pe_ratio_max} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pe_ratio_max: v })} />
                                <FilterInput label="PB 最小值" value={fundamentalFilters.pb_ratio_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pb_ratio_min: v })} />
                                <FilterInput label="PB 最大值" value={fundamentalFilters.pb_ratio_max} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, pb_ratio_max: v })} />
                                <FilterInput label="ROE 最小值 (%)" value={fundamentalFilters.roe_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, roe_min: v })} />
                                <FilterInput label="营收增速最小值 (%)" value={fundamentalFilters.revenue_growth_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, revenue_growth_min: v })} />
                                <FilterInput label="净利增速最小值 (%)" value={fundamentalFilters.earnings_growth_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, earnings_growth_min: v })} />
                                <FilterInput label="股息率最小值 (%)" value={fundamentalFilters.dividend_yield_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, dividend_yield_min: v })} />
                                <FilterInput label="市值最小值 (亿)" value={fundamentalFilters.market_cap_min} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, market_cap_min: v })} />
                                <FilterInput label="市值最大值 (亿)" value={fundamentalFilters.market_cap_max} onChange={(v) => setFundamentalFilters({ ...fundamentalFilters, market_cap_max: v })} />
                                <div className="md:col-span-3">
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">行业</label>
                                    <select
                                        value={fundamentalFilters.sector}
                                        onChange={(e) => setFundamentalFilters({ ...fundamentalFilters, sector: e.target.value })}
                                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                                        aria-label="选择行业"
                                        title="选择行业"
                                    >
                                        <option value="">全部</option>
                                        {sectors.map((s) => (
                                            <option key={s} value={s}>{s}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <button onClick={handleRunFundamental} className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 font-medium" type="button">
                                <Search size={18} /> 运行筛选
                            </button>
                        </div>

                        {loading && (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                <span className="ml-3 text-slate-500">筛选中...</span>
                            </div>
                        )}

                        {!loading && screenerResults.length > 0 && (
                            <ResultsTable stocks={screenerResults} count={resultCount} />
                        )}
                    </div>
                )}

                {/* Technical Filters */}
                {activeTab === "technical" && (
                    <div className="space-y-6">
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <BarChart3 className="h-5 w-5 text-slate-400" />
                                技术面筛选条件
                            </h3>
                            <div className="grid md:grid-cols-2 gap-4">
                                <FilterInput label="RSI 最小值" value={technicalFilters.rsi_min} onChange={(v) => setTechnicalFilters({ ...technicalFilters, rsi_min: v })} />
                                <FilterInput label="RSI 最大值" value={technicalFilters.rsi_max} onChange={(v) => setTechnicalFilters({ ...technicalFilters, rsi_max: v })} />
                                <div className="md:col-span-2 grid grid-cols-3 gap-4">
                                    <label className="flex items-center gap-2 p-3 border border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={technicalFilters.macd_golden_cross}
                                            onChange={(e) => setTechnicalFilters({ ...technicalFilters, macd_golden_cross: e.target.checked })}
                                        />
                                        <span className="text-sm text-slate-700 dark:text-slate-300">MACD 金叉</span>
                                    </label>
                                    <label className="flex items-center gap-2 p-3 border border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={technicalFilters.above_ma20}
                                            onChange={(e) => setTechnicalFilters({ ...technicalFilters, above_ma20: e.target.checked })}
                                        />
                                        <span className="text-sm text-slate-700 dark:text-slate-300">股价 &gt; MA20</span>
                                    </label>
                                    <label className="flex items-center gap-2 p-3 border border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={technicalFilters.above_ma50}
                                            onChange={(e) => setTechnicalFilters({ ...technicalFilters, above_ma50: e.target.checked })}
                                        />
                                        <span className="text-sm text-slate-700 dark:text-slate-300">股价 &gt; MA50</span>
                                    </label>
                                </div>
                            </div>
                            <button onClick={handleRunTechnical} className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 font-medium" type="button">
                                <Search size={18} /> 运行筛选
                            </button>
                        </div>

                        {loading && (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                <span className="ml-3 text-slate-500">筛选中...</span>
                            </div>
                        )}

                        {!loading && screenerResults.length > 0 && (
                            <ResultsTable stocks={screenerResults} count={resultCount} />
                        )}
                    </div>
                )}
            </div>
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

function FilterInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
    return (
        <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{label}</label>
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                placeholder="0"
                aria-label={label}
            />
        </div>
    );
}

function ResultsTable({ stocks, count }: { stocks: StockScreenerResult[]; count: number }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">筛选结果</span>
                <span className="text-xs text-slate-500">{count} 只股票</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">代码</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">名称</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">现价</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">PE</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">PB</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ROE</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">营收增速</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">股息率</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">行业</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                        {stocks.map((stock) => (
                            <tr key={stock.ticker} className="hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                                <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{stock.ticker}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.name}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">${stock.current_price?.toFixed(2)}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.pe_ratio?.toFixed(2) || "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.pb_ratio?.toFixed(2) || "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.roe ? (stock.roe * 100).toFixed(1) + "%" : "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.revenue_growth ? (stock.revenue_growth * 100).toFixed(1) + "%" : "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.dividend_yield ? (stock.dividend_yield * 100).toFixed(1) + "%" : "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{stock.sector || "-"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
