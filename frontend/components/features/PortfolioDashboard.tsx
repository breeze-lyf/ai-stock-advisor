"use client";

import { useState, useEffect } from "react";
import { 
    LayoutDashboard, 
    TrendingUp, 
    TrendingDown, 
    ShieldCheck, 
    AlertTriangle, 
    RefreshCw,
    BrainCircuit,
    PieChart,
    ChevronRight,
    BookOpen
} from "lucide-react";
import { 
    getPortfolioSummary, 
    analyzePortfolio 
} from "@/lib/api";
import { 
    PortfolioSummary, 
    PortfolioAnalysisResponse 
} from "@/types";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";

interface PortfolioDashboardProps {
    onSelectTicker: (ticker: string) => void;
}

export function PortfolioDashboard({ onSelectTicker }: PortfolioDashboardProps) {
    const [summary, setSummary] = useState<PortfolioSummary | null>(null);
    const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [loadingAnalysis, setLoadingAnalysis] = useState(false);
    const [showReport, setShowReport] = useState(false);

    const fetchData = async () => {
        // Step 1: Fetch and display summary immediately
        setLoading(true);
        try {
            const summaryData = await getPortfolioSummary();
            setSummary(summaryData);
            setLoading(false); // Show content as soon as summary is ready
            
            // Step 2: Fetch latest analysis in background
            setLoadingAnalysis(true);
            try {
                const api = await import("@/lib/api");
                const latestAnalysis = await api.getLatestPortfolioAnalysis();
                if (latestAnalysis) {
                    setAnalysis(latestAnalysis);
                }
            } catch (err) {
                console.error("Analysis background fetch failed:", err);
            } finally {
                setLoadingAnalysis(false);
            }
        } catch (error) {
            console.error("Failed to fetch portfolio data:", error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleAnalyze = async () => {
        setAnalyzing(true);
        try {
            const result = await analyzePortfolio();
            setAnalysis(result);
        } catch (error) {
            console.error("Analysis failed:", error);
        } finally {
            setAnalyzing(false);
        }
    };

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
                    <p className="text-sm font-medium text-slate-500">正在生成持仓透视...</p>
                </div>
            </div>
        );
    }

    const isProfit = (summary?.total_unrealized_pl || 0) >= 0;

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50 dark:bg-slate-950 custom-scrollbar">
            <div className="grid grid-cols-12 gap-4 max-w-7xl mx-auto">
                
                {/* Top Stats Banner */}
                <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
                        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-500/5 blur-3xl rounded-full" />
                        
                        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                            <div className="space-y-1">
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">总资产净值 (Total Equity)</span>
                                <div className="flex items-baseline gap-2">
                                    <h2 className="text-4xl font-bold tracking-tighter text-slate-900 dark:text-white">
                                        ${summary?.total_market_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </h2>
                                    <span className="text-[10px] font-bold text-slate-400">USD</span>
                                </div>
                            </div>

                            <div className="flex gap-8">
                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">累计盈亏 (P/L)</span>
                                    <div className={clsx(
                                        "flex items-center gap-1.5 font-bold text-lg tabular-nums",
                                        isProfit ? "text-emerald-500" : "text-rose-500"
                                    )}>
                                        {isProfit ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                                        {isProfit ? "+" : ""}{summary?.total_unrealized_pl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                    <div className={clsx(
                                        "text-[10px] font-bold px-2 py-0.5 rounded-full inline-block",
                                        isProfit ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                                    )}>
                                        {summary?.total_pl_percent.toFixed(2)}%
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">今日变动 (Day Change)</span>
                                    <div className={clsx(
                                        "flex items-center gap-1.5 font-bold text-lg tabular-nums",
                                        (summary?.day_change || 0) >= 0 ? "text-emerald-500" : "text-rose-500"
                                    )}>
                                        {(summary?.day_change || 0) >= 0 ? "+" : ""}{summary?.day_change.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Holdings Table */}
                    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                        <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2">
                                <LayoutDashboard className="h-3.5 w-3.5 text-blue-500" />
                                资产持仓细节 (Holdings)
                            </h3>
                            <div className="text-[10px] text-slate-400 font-bold">
                                共 {summary?.holdings.length} 个标的
                            </div>
                        </div>
                        
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="bg-slate-50/50 dark:bg-slate-800/20 text-[10px] font-bold text-slate-400 uppercase tracking-tight">
                                        <th className="px-5 py-2.5">代码/名称</th>
                                        <th className="px-3 py-2.5 text-right">持有数量</th>
                                        <th className="px-3 py-2.5 text-right">平均成本</th>
                                        <th className="px-3 py-2.5 text-right">当前价格</th>
                                        <th className="px-3 py-2.5 text-right">总价值</th>
                                        <th className="px-3 py-2.5 text-right">盈亏</th>
                                        <th className="px-3 py-2.5 text-right">RRR</th>
                                        <th className="px-5 py-2.5"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                                    {summary?.holdings.map((item) => (
                                        <tr 
                                            key={item.ticker} 
                                            className="hover:bg-slate-50/80 dark:hover:bg-slate-800/30 transition-colors group cursor-pointer"
                                            onClick={() => onSelectTicker(item.ticker)}
                                        >
                                            <td className="px-5 py-3">
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-slate-900 dark:text-white text-sm">{item.ticker}</span>
                                                    <span className="text-[10px] text-slate-400 truncate max-w-[100px]">{item.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-3 py-3 text-right font-bold text-xs tabular-nums text-slate-600 dark:text-slate-400">{item.quantity}</td>
                                            <td className="px-3 py-3 text-right font-bold text-xs tabular-nums text-slate-600 dark:text-slate-400">${item.avg_cost.toFixed(2)}</td>
                                            <td className="px-3 py-3 text-right font-bold text-xs tabular-nums text-slate-900 dark:text-white">${item.current_price.toFixed(2)}</td>
                                            <td className="px-3 py-3 text-right">
                                                <span className="font-bold text-xs tabular-nums text-slate-900 dark:text-white">${item.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                                            </td>
                                            <td className="px-3 py-3 text-right">
                                                <div className="flex flex-col items-end">
                                                    <span className={clsx(
                                                        "font-bold text-xs tabular-nums",
                                                        item.unrealized_pl >= 0 ? "text-emerald-500" : "text-rose-500"
                                                    )}>
                                                        {item.unrealized_pl >= 0 ? "+" : ""}{item.unrealized_pl.toFixed(2)}
                                                    </span>
                                                    <span className={clsx(
                                                        "text-[10px] font-bold",
                                                        item.pl_percent >= 0 ? "text-emerald-500/70" : "text-rose-500/70"
                                                    )}>
                                                        {item.pl_percent.toFixed(2)}%
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-3 py-3 text-right">
                                                <span className={clsx(
                                                    "text-[10px] font-bold px-1.5 py-0.5 rounded border",
                                                    (item.risk_reward_ratio || 0) > 2 ? "bg-emerald-50 text-emerald-600 border-emerald-200" : 
                                                    (item.risk_reward_ratio || 0) > 1 ? "bg-blue-50 text-blue-600 border-blue-200" :
                                                    "bg-slate-50 text-slate-500 border-slate-200"
                                                )}>
                                                    {item.risk_reward_ratio ? item.risk_reward_ratio.toFixed(2) : "--"}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                                <ChevronRight className="h-3 w-3 text-slate-400" />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Sidebar: Sector Distribution & AI Health */}
                <div className="col-span-12 lg:col-span-4 space-y-4">
                    
                    {/* AI Health Diagnostic Card */}
                    <div className="bg-slate-900 dark:bg-blue-950/20 rounded-2xl p-5 border border-slate-800 dark:border-blue-900/30 shadow-sm relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            <BrainCircuit className="h-16 w-16 text-blue-500" />
                        </div>
                        
                        <h3 className="text-white font-bold text-xs uppercase tracking-widest flex items-center gap-2 mb-4">
                            <BrainCircuit className="h-3.5 w-3.5 text-blue-400" />
                            AI 组合诊断 (Health)
                        </h3>

                        {(!analysis && loadingAnalysis) ? (
                            <div className="py-8 flex flex-col items-center justify-center gap-3 animate-pulse">
                                <div className="h-10 w-10 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                                    <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
                                </div>
                                <p className="text-slate-500 text-[10px] font-bold">同步历史诊断...</p>
                            </div>
                        ) : !analysis ? (
                            <div className="py-6 flex flex-col items-center text-center gap-3">
                                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                    <ShieldCheck className="h-6 w-6 text-blue-400" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-slate-300 text-xs font-bold">获取 AI 专业意见</p>
                                    <p className="text-slate-500 text-[10px] px-4">审视组合风险、行业集中度并获得策略建议。</p>
                                </div>
                                <Button 
                                    onClick={handleAnalyze} 
                                    disabled={analyzing}
                                    className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl mt-2 h-10 text-xs shadow-lg shadow-blue-900/20"
                                >
                                    {analyzing ? (
                                        <>
                                            <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
                                            分析中...
                                        </>
                                    ) : "立即诊断组合健康"}
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                                <div className="flex items-center gap-3">
                                    <div className="relative flex items-center justify-center">
                                        <svg className="h-12 w-12 -rotate-90">
                                            <circle 
                                                cx="24" cy="24" r="20" 
                                                className="stroke-slate-800 fill-none" 
                                                strokeWidth="4"
                                            />
                                            <circle 
                                                cx="24" cy="24" r="20" 
                                                className="stroke-blue-500 fill-none transition-all duration-1000" 
                                                strokeWidth="4"
                                                strokeDasharray={125}
                                                strokeDashoffset={125 - (125 * (analysis.health_score || 0)) / 100}
                                            />
                                        </svg>
                                        <span className="absolute text-sm font-bold text-white">{analysis.health_score}</span>
                                    </div>
                                    <div className="min-w-0">
                                        <span className={clsx(
                                            "inline-block px-1.5 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-tight mb-1",
                                            analysis.risk_level === "低" ? "bg-emerald-500/20 text-emerald-400" :
                                            analysis.risk_level === "中" ? "bg-yellow-500/20 text-yellow-400" :
                                            "bg-rose-500/20 text-rose-400"
                                        )}>
                                            风险: {analysis.risk_level}
                                        </span>
                                        <p className="text-white font-bold text-xs leading-tight truncate">{analysis.summary}</p>
                                    </div>
                                </div>

                                <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/50">
                                    <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-3">
                                        {analysis.strategic_advice}
                                    </p>
                                </div>

                                <div className="flex gap-2">
                                    <Dialog open={showReport} onOpenChange={setShowReport}>
                                        <DialogTrigger asChild>
                                            <Button 
                                                variant="secondary"
                                                className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl h-9 text-[10px] gap-1.5"
                                            >
                                                <BookOpen className="h-3 w-3" />
                                                深度报告
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent className="max-w-2xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 p-0 overflow-hidden rounded-2xl">
                                            <DialogHeader className="p-5 border-b border-slate-100 dark:border-slate-800 flex flex-row items-center justify-between bg-slate-50/50 dark:bg-slate-800/20 space-y-0 text-left">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                                        <BrainCircuit className="h-4 w-4 text-blue-500" />
                                                    </div>
                                                    <div className="text-left">
                                                        <DialogTitle className="font-bold text-base text-slate-900 dark:text-white leading-tight">
                                                            AI 深度诊断报告
                                                        </DialogTitle>
                                                        <DialogDescription className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                                                            Portfolio Deep Insight Report
                                                        </DialogDescription>
                                                    </div>
                                                </div>
                                            </DialogHeader>
                                            
                                            <ScrollArea className="h-[50vh] p-6">
                                                <div className="prose prose-slate dark:prose-invert max-w-none text-xs prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-headings:text-slate-900 dark:prose-headings:text-white prose-strong:text-slate-900 dark:prose-strong:text-white">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.detailed_report}</ReactMarkdown>
                                                </div>
                                            </ScrollArea>
                                            
                                            <div className="p-3 bg-slate-50 dark:bg-slate-800/30 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-[10px]">
                                                <span className="font-bold text-slate-400">报告生成时间: {new Date(analysis.created_at).toLocaleString()}</span>
                                                <Button variant="ghost" size="sm" onClick={() => setShowReport(false)} className="font-bold text-[10px] h-7">关闭</Button>
                                            </div>
                                        </DialogContent>
                                    </Dialog>

                                    <Button 
                                        variant="outline" 
                                        onClick={handleAnalyze}
                                        disabled={analyzing}
                                        className="bg-transparent border-slate-700 hover:bg-slate-800 text-slate-400 font-bold rounded-xl h-9 px-2.5"
                                    >
                                        <RefreshCw className={clsx("h-3 w-3", analyzing && "animate-spin")} />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Sector Exposure Chart */}
                    <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm">
                        <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2 mb-4">
                            <PieChart className="h-3.5 w-3.5 text-emerald-500" />
                            行业覆盖 / 分布
                        </h3>
                        
                        <div className="space-y-4">
                            {summary?.sector_exposure.sort((a, b) => b.value - a.value).map((s, idx) => (
                                <div key={idx} className="space-y-1">
                                    <div className="flex justify-between text-[10px] font-bold uppercase tracking-tight">
                                        <span className="text-slate-500 dark:text-slate-400">{s.sector === "Unknown" ? "未归类/其他" : s.sector}</span>
                                        <span className="text-slate-900 dark:text-white">{s.weight.toFixed(1)}%</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                        <div 
                                            className={clsx(
                                                "h-full rounded-full transition-all duration-1000",
                                                idx === 0 ? "bg-blue-500" :
                                                idx === 1 ? "bg-emerald-500" : 
                                                idx === 2 ? "bg-violet-500" : "bg-slate-400"
                                            )} 
                                            style={{ width: `${s.weight}%` }} 
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6 p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-center">
                            <p className="text-[10px] text-slate-400 font-bold">
                                建议：避免行业集中度超过 40% 以降低系统风险。
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
