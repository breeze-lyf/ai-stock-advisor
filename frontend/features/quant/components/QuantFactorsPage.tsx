"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useQuantFactors, useFactorICAnalysis, useFactorLayeredBacktest } from "@/features/quant/hooks/useQuantFactors";
import { LineChart } from "@/components/charts";
import { RefreshCw, BrainCircuit, TrendingUp, BarChart3 } from "lucide-react";
import { DashboardHeader } from "@/components/features/DashboardHeader";
import { SearchDialog } from "@/components/features/SearchDialog";
import { useDashboardPortfolioData } from "@/features/dashboard/hooks/useDashboardPortfolioData";
import type { DashboardTab } from "@/features/dashboard/hooks/useDashboardRouteState";

const CATEGORIES = ["MOMENTUM", "VALUE", "GROWTH", "QUALITY", "VOLATILITY", "LIQUIDITY", "TECHNICAL"];

export default function QuantPage() {
    const { isAuthenticated, user } = useAuth();
    const { portfolio, user: userProfile } = useDashboardPortfolioData(isAuthenticated);
    const { factors, loading, error, refresh } = useQuantFactors();
    const [selectedFactor, setSelectedFactor] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"list" | "ic" | "backtest">("list");
    const [dateRange, setDateRange] = useState({
        start: "2025-01-01",
        end: "2026-04-07",
    });
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [activeHeaderTab, setActiveHeaderTab] = useState<DashboardTab>("analysis");

    const { data: icData, loading: icLoading, fetchICAnalysis } = useFactorICAnalysis(
        selectedFactor || "",
        dateRange.start,
        dateRange.end,
    );

    const { data: backtestData, loading: backtestLoading, fetchBacktest } = useFactorLayeredBacktest(
        selectedFactor || "",
        dateRange.start,
        dateRange.end,
    );

    const handleFactorSelect = (factorId: string) => {
        setSelectedFactor(factorId);
        setActiveTab("ic");
    };

    const handleICAnalysis = () => {
        if (selectedFactor) fetchICAnalysis("rank", 5);
    };

    const handleLayeredBacktest = () => {
        if (selectedFactor) fetchBacktest(10);
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
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-linear-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <BrainCircuit className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white">量化因子</h1>
                            <p className="text-xs text-slate-500 dark:text-slate-400">因子分析 · IC 检验 · 分层回测</p>
                        </div>
                    </div>
                    <button
                        onClick={() => refresh()}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1.5 font-bold"
                        type="button"
                    >
                        <RefreshCw size={14} /> 刷新
                    </button>
                </div>

                {/* Tab Navigation */}
                <div className="flex gap-2">
                    <TabButton
                        active={activeTab === "list"}
                        onClick={() => setActiveTab("list")}
                        label="因子列表"
                    />
                    <TabButton
                        active={activeTab === "ic"}
                        onClick={() => { setActiveTab("ic"); handleICAnalysis(); }}
                        disabled={!selectedFactor}
                        label="IC 分析"
                    />
                    <TabButton
                        active={activeTab === "backtest"}
                        onClick={() => { setActiveTab("backtest"); handleLayeredBacktest(); }}
                        disabled={!selectedFactor}
                        label="分层回测"
                    />
                </div>

                {/* Factor List */}
                {activeTab === "list" && (
                    <div className="space-y-4">
                        {/* Category Filters */}
                        <div className="flex gap-2 flex-wrap">
                            <button
                                onClick={() => setSelectedFactor(null)}
                                type="button"
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                                    !selectedFactor
                                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                                        : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-blue-300"
                                }`}
                            >
                                全部
                            </button>
                            {CATEGORIES.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => setSelectedFactor(cat === selectedFactor ? null : cat)}
                                    type="button"
                                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                                        cat === selectedFactor
                                            ? "bg-blue-600 text-white"
                                            : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-blue-300"
                                    }`}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>

                        {/* Factors Table */}
                        {loading && (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                <span className="ml-3 text-slate-500">加载中...</span>
                            </div>
                        )}

                        {error && (
                            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
                                {error}
                            </div>
                        )}

                        {!loading && !error && factors && factors.length > 0 && (
                            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                                <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">因子库</span>
                                    <span className="text-xs text-slate-500">{factors.length} 个因子</span>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead className="bg-slate-50 dark:bg-slate-900">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">因子代码</th>
                                                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">因子名称</th>
                                                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">类别</th>
                                                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">IC</th>
                                                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">IR</th>
                                                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">多空收益</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                            {factors
                                                .filter((f) => !selectedFactor || f.category === selectedFactor)
                                                .map((factor) => (
                                                    <tr
                                                        key={factor.id}
                                                        onClick={() => handleFactorSelect(factor.id)}
                                                        className="hover:bg-blue-50 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                                                    >
                                                        <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">{factor.id}</td>
                                                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{factor.name}</td>
                                                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                                                            <span className="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-700 text-xs font-bold">{factor.category}</span>
                                                        </td>
                                                        <td className={`px-4 py-3 text-sm text-right font-bold ${factor.ic_mean && factor.ic_mean >= 0.05 ? "text-emerald-600" : "text-slate-600 dark:text-slate-300"}`}>
                                                            {factor.ic_mean?.toFixed(3) || "--"}
                                                        </td>
                                                        <td className={`px-4 py-3 text-sm text-right font-bold ${factor.ic_ir && factor.ic_ir >= 0.5 ? "text-emerald-600" : "text-slate-600 dark:text-slate-300"}`}>
                                                            {factor.ic_ir?.toFixed(2) || "--"}
                                                        </td>
                                                        <td className={`px-4 py-3 text-sm text-right font-bold ${factor.annual_return && factor.annual_return >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                                            {(factor.annual_return || 0) >= 0 ? "+" : ""}{(factor.annual_return || 0) * 100}%
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {!loading && !error && (!factors || factors.length === 0) && (
                                <div className="text-center py-12 text-slate-400">
                                    <BrainCircuit className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                    <p className="text-sm">暂无因子数据</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* IC Analysis */}
                    {activeTab === "ic" && selectedFactor && (
                        <div className="space-y-4">
                            <div className="flex items-center gap-4">
                                <div className="flex-1">
                                    <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                                        因子：{selectedFactor}
                                    </h3>
                                </div>
                            </div>

                            {icLoading && (
                                <div className="flex items-center justify-center py-12">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                    <span className="ml-3 text-slate-500">分析中...</span>
                                </div>
                            )}

                            {!icLoading && icData && (
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                        <h4 className="text-xs font-bold text-slate-500 mb-3 flex items-center gap-2">
                                            <TrendingUp className="w-4 h-4" /> IC 序列
                                        </h4>
                                        <LineChart
                                            data={icData.ic_series?.map((d) => ({
                                                x: d.trade_date,
                                                y: d.ic,
                                            })) || []}
                                            height={200}
                                        />
                                    </div>
                                    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                        <h4 className="text-xs font-bold text-slate-500 mb-3 flex items-center gap-2">
                                            <BarChart3 className="w-4 h-4" /> IC 统计
                                        </h4>
                                        <div className="space-y-2">
                                            <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                                                <span className="text-xs text-slate-500">Mean IC</span>
                                                <span className="text-sm font-bold">{icData.ic_mean?.toFixed(4) || "--"}</span>
                                            </div>
                                            <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                                                <span className="text-xs text-slate-500">IC IR</span>
                                                <span className="text-sm font-bold">{icData.ic_ir?.toFixed(2) || "--"}</span>
                                            </div>
                                            <div className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700">
                                                <span className="text-xs text-slate-500">T-Stat</span>
                                                <span className="text-sm font-bold">{icData.t_stat?.toFixed(2) || "--"}</span>
                                            </div>
                                            <div className="flex justify-between items-center py-2">
                                                <span className="text-xs text-slate-500">样本数</span>
                                                <span className="text-sm font-bold">{icData.sample_size || "--"}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Layered Backtest */}
                    {activeTab === "backtest" && selectedFactor && (
                        <div className="space-y-4">
                            {backtestLoading && (
                                <div className="flex items-center justify-center py-12">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                                    <span className="ml-3 text-slate-500">回测中...</span>
                                </div>
                            )}

                            {!backtestLoading && backtestData && (
                                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                    <h4 className="text-xs font-bold text-slate-500 mb-3">分层累计收益</h4>
                                    <LineChart
                                        data={backtestData.equity_curves?.["1"]?.map((d) => ({
                                            x: d.date,
                                            y: d.equity,
                                        })) || []}
                                        height={300}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}

function TabButton({ active, onClick, label, disabled }: { active: boolean; onClick: () => void; label: string; disabled?: boolean }) {
    return (
        <button
            onClick={onClick}
            type="button"
            disabled={disabled}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                active
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
            }`}
        >
            {label}
        </button>
    );
}
