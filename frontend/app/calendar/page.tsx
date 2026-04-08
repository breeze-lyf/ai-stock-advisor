"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
    getEconomicEvents,
    getHighImpactEvents,
    getEarningsEvents,
    getMegaCapEarnings,
    getPortfolioEarnings,
    type EconomicEvent,
    type EarningsEvent,
} from "@/features/calendar/api";
import { Calendar as CalendarIcon, Globe, Briefcase, Star, TrendingUp, Filter, AlertCircle, ArrowLeft } from "lucide-react";

type CalendarTab = "economic" | "earnings" | "mega-cap" | "portfolio";

export default function CalendarPage() {
    const router = useRouter();
    const { user } = useAuth();
    const [calendarTab, setCalendarTab] = useState<CalendarTab>("economic");
    const [economicEvents, setEconomicEvents] = useState<EconomicEvent[]>([]);
    const [earningsEvents, setEarningsEvents] = useState<EarningsEvent[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [dateFilter, setDateFilter] = useState({ start: "", end: "" });
    const [countryFilter, setCountryFilter] = useState("");
    const [importanceFilter, setImportanceFilter] = useState<number | "">("");
    const [resultCount, setResultCount] = useState(0);

    useEffect(() => {
        setError(null);
        if (calendarTab === "economic") {
            handleLoadEconomic();
        } else if (calendarTab === "earnings") {
            handleLoadEarnings();
        } else if (calendarTab === "mega-cap") {
            handleLoadMegaCap();
        } else if (calendarTab === "portfolio") {
            handleLoadPortfolio();
        }
    }, [calendarTab]);

    const handleLoadEconomic = async () => {
        setLoading(true);
        setError(null);
        try {
            const filters: Record<string, unknown> = { limit: 100 };
            if (dateFilter.start) filters.start_date = dateFilter.start;
            if (dateFilter.end) filters.end_date = dateFilter.end;
            if (countryFilter) filters.country = countryFilter;
            if (importanceFilter !== "") filters.importance = importanceFilter;

            const result = await getEconomicEvents(filters);
            setEconomicEvents(result.events);
            setResultCount(result.count);
        } catch (err) {
            console.error("Failed to load economic events:", err);
            setError("加载失败：" + (err as Error).message);
            setEconomicEvents([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleLoadHighImpact = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await getHighImpactEvents(7);
            setEconomicEvents(result.events);
            setResultCount(result.count);
        } catch (err) {
            console.error("Failed to load high impact events:", err);
            setError("加载失败：" + (err as Error).message);
            setEconomicEvents([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleLoadEarnings = async () => {
        setLoading(true);
        setError(null);
        try {
            const filters: Record<string, unknown> = { limit: 100 };
            if (dateFilter.start) filters.start_date = dateFilter.start;
            if (dateFilter.end) filters.end_date = dateFilter.end;

            const result = await getEarningsEvents(filters);
            setEarningsEvents(result.events);
            setResultCount(result.count);
        } catch (err) {
            console.error("Failed to load earnings events:", err);
            setError("加载失败：" + (err as Error).message);
            setEarningsEvents([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleLoadMegaCap = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await getMegaCapEarnings(30);
            setEarningsEvents(result.events);
            setResultCount(result.count);
        } catch (err) {
            console.error("Failed to load mega cap earnings:", err);
            setError("加载失败：" + (err as Error).message);
            setEarningsEvents([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const handleLoadPortfolio = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await getPortfolioEarnings(14);
            setEarningsEvents(result.events);
            setResultCount(result.count);
        } catch (err) {
            console.error("Failed to load portfolio earnings:", err);
            setError("加载失败：" + (err as Error).message);
            setEarningsEvents([]);
            setResultCount(0);
        } finally {
            setLoading(false);
        }
    };

    const getImportanceLabel = (level: number) => {
        if (level === 3) return { label: "高", className: "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300" };
        if (level === 2) return { label: "中", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300" };
        return { label: "低", className: "bg-slate-100 text-slate-700 dark:bg-slate-900/20 dark:text-slate-300" };
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
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white">财经日历</h1>
                            <p className="text-xs text-slate-500 dark:text-slate-400">宏观事件 · 财报发布</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="p-6">
                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    <TabButton active={calendarTab === "economic"} onClick={() => setCalendarTab("economic")} icon={<Globe />} label="宏观事件" />
                    <TabButton active={calendarTab === "earnings"} onClick={() => setCalendarTab("earnings")} icon={<Briefcase />} label="财报日历" />
                    <TabButton active={calendarTab === "mega-cap"} onClick={() => setCalendarTab("mega-cap")} icon={<Star />} label="巨头财报" />
                    <TabButton active={calendarTab === "portfolio"} onClick={() => setCalendarTab("portfolio")} icon={<TrendingUp />} label="持仓财报" />
                </div>

                {/* Filters */}
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 mb-6">
                    <div className="flex items-center gap-4 flex-wrap">
                        <div className="flex items-center gap-2">
                            <Filter className="h-4 w-4 text-slate-400" />
                            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">筛选条件:</span>
                        </div>
                        <input
                            type="date"
                            value={dateFilter.start}
                            onChange={(e) => setDateFilter({ ...dateFilter, start: e.target.value })}
                            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                            aria-label="开始日期"
                        />
                        <span className="text-slate-400">至</span>
                        <input
                            type="date"
                            value={dateFilter.end}
                            onChange={(e) => setDateFilter({ ...dateFilter, end: e.target.value })}
                            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                            aria-label="结束日期"
                        />
                        <select
                            value={countryFilter}
                            onChange={(e) => setCountryFilter(e.target.value)}
                            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                            aria-label="选择国家"
                            title="选择国家"
                        >
                            <option value="">全部国家</option>
                            <option value="US">美国</option>
                            <option value="CN">中国</option>
                            <option value="EU">欧盟</option>
                            <option value="JP">日本</option>
                            <option value="UK">英国</option>
                        </select>
                        <select
                            value={importanceFilter}
                            onChange={(e) => setImportanceFilter(e.target.value ? Number(e.target.value) : "")}
                            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-sm"
                            aria-label="选择重要性"
                            title="选择重要性"
                        >
                            <option value="">全部重要性</option>
                            <option value="3">高 (3 星)</option>
                            <option value="2">中 (2 星)</option>
                            <option value="1">低 (1 星)</option>
                        </select>
                        <button
                            onClick={calendarTab === "economic" ? handleLoadEconomic : handleLoadEarnings}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                            type="button"
                        >
                            应用筛选
                        </button>
                        {calendarTab === "economic" && (
                            <button
                                onClick={handleLoadHighImpact}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium flex items-center gap-1"
                                type="button"
                            >
                                <Star size={14} /> 高影响事件
                            </button>
                        )}
                    </div>
                </div>

                {/* Error State */}
                {error && (
                    <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                        <div>
                            <p className="text-sm font-medium text-red-800 dark:text-red-200">{error}</p>
                            <button
                                onClick={calendarTab === "economic" ? handleLoadEconomic : calendarTab === "mega-cap" ? handleLoadMegaCap : calendarTab === "portfolio" ? handleLoadPortfolio : handleLoadEarnings}
                                className="mt-2 text-xs text-red-600 hover:text-red-700 dark:text-red-300 font-medium"
                                type="button"
                            >
                                重试
                            </button>
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                        <span className="ml-3 text-slate-500">加载中...</span>
                    </div>
                )}

                {/* Economic Events */}
                {calendarTab === "economic" && !loading && !error && (
                    <EventTable events={economicEvents} getImportanceLabel={getImportanceLabel} count={resultCount} />
                )}

                {/* Earnings Events */}
                {(calendarTab === "earnings" || calendarTab === "mega-cap" || calendarTab === "portfolio") && !loading && !error && (
                    <EarningsTable events={earningsEvents} count={resultCount} />
                )}

                {/* Empty State */}
                {!loading && !error && economicEvents.length === 0 && calendarTab === "economic" && (
                    <div className="text-center py-12 text-slate-400">
                        <Globe className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p className="text-sm">暂无宏观事件数据</p>
                        <button onClick={handleLoadEconomic} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium" type="button">
                            加载事件
                        </button>
                    </div>
                )}

                {!loading && !error && earningsEvents.length === 0 && (calendarTab === "earnings" || calendarTab === "mega-cap" || calendarTab === "portfolio") && (
                    <div className="text-center py-12 text-slate-400">
                        <Briefcase className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p className="text-sm">暂无财报数据</p>
                        <button
                            onClick={calendarTab === "mega-cap" ? handleLoadMegaCap : calendarTab === "portfolio" ? handleLoadPortfolio : handleLoadEarnings}
                            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                            type="button"
                        >
                            加载财报
                        </button>
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

function EventTable({ events, getImportanceLabel, count }: { events: EconomicEvent[]; getImportanceLabel: (level: number) => { label: string; className: string }; count: number }) {
    if (events.length === 0) return null;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">宏观事件</span>
                <span className="text-xs text-slate-500">{count} 个事件</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">日期</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">事件</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">国家</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">重要性</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">类型</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">前值</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">预测</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                        {events.map((event) => (
                            <tr key={event.id} className="hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                                <td className="px-4 py-3 text-sm text-slate-900 dark:text-white">
                                    <div>{event.event_date}</div>
                                    {event.event_time && <div className="text-xs text-slate-500">{event.event_time}</div>}
                                </td>
                                <td className="px-4 py-3">
                                    <div className="font-medium text-slate-900 dark:text-white">{event.event_name}</div>
                                    {event.impact && <div className="text-xs text-slate-500">{event.impact}</div>}
                                </td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{event.country}</td>
                                <td className="px-4 py-3">
                                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${getImportanceLabel(event.importance).className}`}>
                                        {getImportanceLabel(event.importance).label}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{event.event_type}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{event.previous || "-"}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{event.forecast || "-"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function EarningsTable({ events, count }: { events: EarningsEvent[]; count: number }) {
    if (events.length === 0) return null;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">财报发布</span>
                <span className="text-xs text-slate-500">{count} 家公司</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">日期</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">代码</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">公司</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">财报季</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">EPS 预估</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">EPS 实际</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">营收预估</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                        {events.map((event) => (
                            <tr key={event.id} className="hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                                <td className="px-4 py-3 text-sm text-slate-900 dark:text-white">
                                    <div>{event.report_date}</div>
                                    {event.report_time && <div className="text-xs text-slate-500">{event.report_time}</div>}
                                </td>
                                <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{event.ticker}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{event.company_name}</td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                                    {event.quarter && event.fiscal_year ? `Q${event.quarter} FY${event.fiscal_year}` : "-"}
                                </td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                                    {event.eps_estimate ? `$${event.eps_estimate.toFixed(2)}` : "-"}
                                </td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                                    {event.eps_actual !== undefined ? (
                                        <span className={event.eps_actual > (event.eps_estimate || 0) ? "text-green-600 font-bold" : "text-red-600 font-bold"}>
                                            ${event.eps_actual.toFixed(2)}
                                        </span>
                                    ) : "-"}
                                </td>
                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                                    {event.revenue_estimate ? `$${(event.revenue_estimate / 1e9).toFixed(1)}B` : "-"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
