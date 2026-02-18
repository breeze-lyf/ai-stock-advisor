"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { 
    LayoutDashboard, 
    TrendingUp, 
    TrendingDown, 
    ShieldCheck, 
    AlertTriangle, 
    ArrowLeft,
    RefreshCw,
    BrainCircuit,
    PieChart,
    ChevronRight,
    Search,
    BookOpen,
    ExternalLink,
    X
} from "lucide-react";
import Link from "next/link";
import { 
    getPortfolioSummary, 
    analyzePortfolio, 
    getProfile 
} from "@/lib/api";
import { 
    PortfolioSummary, 
    PortfolioAnalysisResponse, 
    UserProfile 
} from "@/types";
import { UserMenu } from "@/components/features/UserMenu";
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

export default function PortfolioPage() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    // State
    const [summary, setSummary] = useState<PortfolioSummary | null>(null);
    const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [showReport, setShowReport] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [summaryData, profileData] = await Promise.all([
                getPortfolioSummary(),
                getProfile()
            ]);
            setSummary(summaryData);
            setUser(profileData);
        } catch (error) {
            console.error("Failed to fetch portfolio data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isAuthenticated) {
            fetchData();
        } else if (typeof window !== 'undefined' && !localStorage.getItem("token")) {
            router.push("/login");
        }
    }, [isAuthenticated]);

    const handleAnalyze = async () => {
        setAnalyzing(true);
        try {
            const result = await analyzePortfolio();
            setAnalysis(result);
        } catch (error) {
            console.error("Analysis failed:", error);
            alert("Portfolio analysis failed. Please check your API keys.");
        } finally {
            setAnalyzing(false);
        }
    };

    if (loading) {
        return (
            <div className="h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                <div className="flex flex-col items-center gap-4">
                    <RefreshCw className="h-8 w-8 text-blue-500 animate-spin" />
                    <p className="text-sm font-medium text-slate-500">正在获取持仓透视...</p>
                </div>
            </div>
        );
    }

    const isProfit = (summary?.total_unrealized_pl || 0) >= 0;

    return (
        <div className="h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
            {/* Header */}
            <header className="flex h-16 items-center px-6 border-b bg-white dark:bg-slate-900 shrink-0 gap-4 z-50">
                <Link href="/" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                    <ArrowLeft className="h-5 w-5 text-slate-500" />
                </Link>
                <div className="flex flex-col">
                    <h1 className="font-black text-lg tracking-tight">我的持仓分析 (Portfolio)</h1>
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Aggregate Health & Insights</span>
                </div>
                <div className="ml-auto flex items-center gap-4">
                    <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={fetchData}
                        className="gap-2 border-slate-200 dark:border-slate-800"
                    >
                        <RefreshCw className="h-3.5 w-3.5" />
                        刷新数据
                    </Button>
                    {user && <UserMenu user={user} />}
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-6 space-y-6">
                <div className="grid grid-cols-12 gap-6 max-w-7xl mx-auto">
                    
                    {/* Top Stats Banner */}
                    <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                        <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
                            {/* Decorative background element */}
                            <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-500/5 blur-3xl rounded-full" />
                            
                            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-8">
                                <div className="space-y-1">
                                    <span className="text-xs font-black text-slate-400 uppercase tracking-widest">总资产净值 (Total Equity)</span>
                                    <div className="flex items-baseline gap-2">
                                        <h2 className="text-5xl font-black tracking-tighter text-slate-900 dark:text-white">
                                            ${summary?.total_market_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </h2>
                                        <span className="text-xs font-bold text-slate-400">USD</span>
                                    </div>
                                </div>

                                <div className="flex gap-12">
                                    <div className="space-y-1">
                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">累计盈亏 (P/L)</span>
                                        <div className={clsx(
                                            "flex items-center gap-1.5 font-black text-xl tabular-nums",
                                            isProfit ? "text-emerald-500" : "text-rose-500"
                                        )}>
                                            {isProfit ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                                            {isProfit ? "+" : ""}{summary?.total_unrealized_pl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </div>
                                        <div className={clsx(
                                            "text-xs font-bold px-2 py-0.5 rounded-full inline-block",
                                            isProfit ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                                        )}>
                                            {summary?.total_pl_percent.toFixed(2)}%
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">今日变动 (Day Change)</span>
                                        <div className={clsx(
                                            "flex items-center gap-1.5 font-black text-xl tabular-nums",
                                            (summary?.day_change || 0) >= 0 ? "text-emerald-500" : "text-rose-500"
                                        )}>
                                            {(summary?.day_change || 0) >= 0 ? "+" : ""}{summary?.day_change.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Holdings Table */}
                        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden min-h-[400px]">
                            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                                <h3 className="font-black text-sm uppercase tracking-wider flex items-center gap-2">
                                    <LayoutDashboard className="h-4 w-4 text-blue-500" />
                                    资产持仓细节 (Holdings)
                                </h3>
                                <div className="text-xs text-slate-400 font-bold">
                                    共 {summary?.holdings.length} 个标的
                                </div>
                            </div>
                            
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="bg-slate-50/50 dark:bg-slate-800/20 text-[10px] font-black text-slate-400 uppercase tracking-tighter">
                                            <th className="px-6 py-3">代码/名称</th>
                                            <th className="px-4 py-3 text-right">持有数量</th>
                                            <th className="px-4 py-3 text-right">平均成本</th>
                                            <th className="px-4 py-3 text-right">当前价格</th>
                                            <th className="px-4 py-3 text-right">总价值</th>
                                            <th className="px-4 py-3 text-right">盈亏</th>
                                            <th className="px-4 py-3 text-right">RRR</th>
                                            <th className="px-6 py-3"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                                        {summary?.holdings.map((item) => (
                                            <tr 
                                                key={item.ticker} 
                                                className="hover:bg-slate-50/80 dark:hover:bg-slate-800/30 transition-colors group cursor-pointer"
                                                onClick={() => router.push(`/?ticker=${item.ticker}`)}
                                            >
                                                <td className="px-6 py-4">
                                                    <div className="flex flex-col">
                                                        <span className="font-black text-slate-900 dark:text-white">{item.ticker}</span>
                                                        <span className="text-[10px] text-slate-400 font-bold truncate max-w-[120px]">{item.name}</span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4 text-right font-bold text-sm tabular-nums text-slate-600 dark:text-slate-400">{item.quantity}</td>
                                                <td className="px-4 py-4 text-right font-bold text-sm tabular-nums text-slate-600 dark:text-slate-400">${item.avg_cost.toFixed(2)}</td>
                                                <td className="px-4 py-4 text-right font-black text-sm tabular-nums text-slate-900 dark:text-white">${item.current_price.toFixed(2)}</td>
                                                <td className="px-4 py-4 text-right">
                                                    <span className="font-black text-sm tabular-nums text-slate-900 dark:text-white">${item.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                                                </td>
                                                <td className="px-4 py-4 text-right">
                                                    <div className="flex flex-col items-end">
                                                        <span className={clsx(
                                                            "font-black text-sm tabular-nums",
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
                                                <td className="px-4 py-4 text-right">
                                                    <span className={clsx(
                                                        "text-[10px] font-black px-1.5 py-0.5 rounded border",
                                                        (item.risk_reward_ratio || 0) > 2 ? "bg-emerald-50 text-emerald-600 border-emerald-200" : 
                                                        (item.risk_reward_ratio || 0) > 1 ? "bg-blue-50 text-blue-600 border-blue-200" :
                                                        "bg-slate-50 text-slate-500 border-slate-200"
                                                    )}>
                                                        {item.risk_reward_ratio ? item.risk_reward_ratio.toFixed(2) : "--"}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <ChevronRight className="h-4 w-4 text-slate-400" />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    {/* Sidebar: Sector Distribution & AI Health */}
                    <div className="col-span-12 lg:col-span-4 space-y-6">
                        
                        {/* AI Health Diagnostic Card */}
                        <div className="bg-slate-900 dark:bg-blue-950/20 rounded-3xl p-6 border border-slate-800 dark:border-blue-900/30 shadow-xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-10">
                                <BrainCircuit className="h-24 w-24 text-blue-500" />
                            </div>
                            
                            <h3 className="text-white font-black text-sm uppercase tracking-widest flex items-center gap-2 mb-6">
                                <BrainCircuit className="h-4 w-4 text-blue-400" />
                                AI 组合诊断 (Health)
                            </h3>

                            {!analysis ? (
                                <div className="py-8 flex flex-col items-center text-center gap-4">
                                    <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                        <ShieldCheck className="h-8 w-8 text-blue-400" />
                                    </div>
                                    <div className="space-y-2">
                                        <p className="text-slate-300 text-sm font-bold">获取 AI 专业意见</p>
                                        <p className="text-slate-500 text-xs px-6">审视组合风险、行业集中度并获得针对性的调仓策略。</p>
                                    </div>
                                    <Button 
                                        onClick={handleAnalyze} 
                                        disabled={analyzing}
                                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl mt-4 h-12"
                                    >
                                        {analyzing ? (
                                            <>
                                                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                                                分析中...
                                            </>
                                        ) : "立即诊断组合健康"}
                                    </Button>
                                </div>
                            ) : (
                                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                    <div className="flex items-center gap-4">
                                        <div className="relative flex items-center justify-center">
                                            <svg className="h-16 w-16 -rotate-90">
                                                <circle 
                                                    cx="32" cy="32" r="28" 
                                                    className="stroke-slate-800 fill-none" 
                                                    strokeWidth="6"
                                                />
                                                <circle 
                                                    cx="32" cy="32" r="28" 
                                                    className="stroke-blue-500 fill-none transition-all duration-1000" 
                                                    strokeWidth="6"
                                                    strokeDasharray={175}
                                                    strokeDashoffset={175 - (175 * (analysis.health_score || 0)) / 100}
                                                />
                                            </svg>
                                            <span className="absolute text-lg font-black text-white">{analysis.health_score}</span>
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs font-black text-slate-400 uppercase tracking-widest">健康等级</span>
                                                <span className={clsx(
                                                    "px-2 py-0.5 rounded-full text-[10px] font-black",
                                                    analysis.risk_level === "低" ? "bg-emerald-500/20 text-emerald-400" :
                                                    analysis.risk_level === "中" ? "bg-yellow-500/20 text-yellow-400" :
                                                    "bg-rose-500/20 text-rose-400"
                                                )}>
                                                    风险: {analysis.risk_level}
                                                </span>
                                            </div>
                                            <p className="text-white font-bold leading-tight mt-1">{analysis.summary}</p>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">战略建议 (Advice)</h4>
                                        <div className="bg-slate-800/50 rounded-2xl p-4 border border-slate-700/50">
                                            <p className="text-slate-300 text-xs leading-relaxed font-medium capitalize prose prose-invert max-w-none">
                                                {analysis.strategic_advice}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="p-3 bg-rose-500/5 border border-rose-500/20 rounded-2xl space-y-2">
                                            <span className="text-[8px] font-black text-rose-500 uppercase tracking-widest flex items-center gap-1">
                                                <AlertTriangle className="h-2 w-2" /> 多空风险
                                            </span>
                                            <ul className="text-[10px] text-rose-200/80 font-bold space-y-1">
                                                {analysis.top_risks?.slice(0, 2).map((r, i) => <li key={i}>• {r}</li>)}
                                                {(!analysis.top_risks || analysis.top_risks.length === 0) && <li>• 暂无明显风险</li>}
                                            </ul>
                                        </div>
                                        <div className="p-3 bg-emerald-500/5 border border-emerald-500/20 rounded-2xl space-y-2">
                                            <span className="text-[8px] font-black text-emerald-500 uppercase tracking-widest flex items-center gap-1">
                                                <TrendingUp className="h-2 w-2" /> 交易机会
                                            </span>
                                            <ul className="text-[10px] text-emerald-200/80 font-bold space-y-1">
                                                {analysis.top_opportunities?.slice(0, 2).map((o, i) => <li key={i}>• {o}</li>)}
                                                {(!analysis.top_opportunities || analysis.top_opportunities.length === 0) && <li>• 暂无明显机会</li>}
                                            </ul>
                                        </div>
                                    </div>
                                    
                                    <div className="flex gap-3">
                                        <Dialog open={showReport} onOpenChange={setShowReport}>
                                            <DialogTrigger asChild>
                                                <Button 
                                                    variant="secondary"
                                                    className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl h-10 text-xs gap-2"
                                                >
                                                    <BookOpen className="h-3.5 w-3.5" />
                                                    阅读深度报告
                                                </Button>
                                            </DialogTrigger>
                                            <DialogContent className="max-w-2xl bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 p-0 overflow-hidden rounded-3xl">
                                                <DialogHeader className="p-6 border-b border-slate-100 dark:border-slate-800 flex flex-row items-center justify-between bg-slate-50/50 dark:bg-slate-800/20 space-y-0 text-left">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-10 h-10 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                                            <BrainCircuit className="h-5 w-5 text-blue-500" />
                                                        </div>
                                                        <div className="text-left">
                                                            <DialogTitle className="font-black text-lg text-slate-900 dark:text-white leading-tight">
                                                                AI 深度诊断报告
                                                            </DialogTitle>
                                                            <DialogDescription className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                                                                Portfolio Deep Insight Report
                                                            </DialogDescription>
                                                        </div>
                                                    </div>
                                                </DialogHeader>
                                                
                                                <ScrollArea className="h-[60vh] p-8">
                                                    <div className="prose prose-slate dark:prose-invert max-w-none prose-xs prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-headings:text-slate-900 dark:prose-headings:text-white prose-strong:text-slate-900 dark:prose-strong:text-white prose-ol:text-slate-600 dark:prose-ol:text-slate-400 prose-ul:text-slate-600 dark:prose-ul:text-slate-400 prose-diagnostic">
                                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.detailed_report}</ReactMarkdown>
                                                    </div>
                                                </ScrollArea>
                                                
                                                <div className="p-4 bg-slate-50 dark:bg-slate-800/30 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                                                    <span className="text-[10px] font-bold text-slate-400 italic">报告生成时间: {new Date(analysis.created_at).toLocaleString()}</span>
                                                    <Button variant="ghost" size="sm" onClick={() => setShowReport(false)} className="font-bold text-xs h-8">关闭</Button>
                                                </div>
                                            </DialogContent>
                                        </Dialog>

                                        <Button 
                                            variant="outline" 
                                            onClick={handleAnalyze}
                                            disabled={analyzing}
                                            className="bg-transparent border-slate-700 hover:bg-slate-800 text-slate-400 font-bold rounded-xl h-10 px-3"
                                        >
                                            <RefreshCw className={clsx("h-3.5 w-3.5", analyzing && "animate-spin")} />
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Sector Exposure Chart */}
                        <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
                            <h3 className="font-black text-sm uppercase tracking-wider flex items-center gap-2 mb-6">
                                <PieChart className="h-4 w-4 text-emerald-500" />
                                行业暴露 / 板块分布
                            </h3>
                            
                            <div className="space-y-5">
                                {summary?.sector_exposure.sort((a, b) => b.value - a.value).map((s, idx) => (
                                    <div key={idx} className="space-y-1.5">
                                        <div className="flex justify-between text-[10px] font-black uppercase tracking-tighter">
                                            <span className="text-slate-600 dark:text-slate-300">{s.sector === "Unknown" ? "未归类/其他" : s.sector}</span>
                                            <span className="text-slate-900 dark:text-white">{s.weight.toFixed(1)}%</span>
                                        </div>
                                        <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
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

                            <div className="mt-8 p-4 bg-slate-50 dark:bg-slate-800/20 rounded-2xl border border-slate-100 dark:border-slate-800">
                                <p className="text-[10px] leading-relaxed text-slate-400 font-bold italic">
                                    提示：过度集中的行业暴露会增加非系统性风险。建议单个行业配比不超过 40%。
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
