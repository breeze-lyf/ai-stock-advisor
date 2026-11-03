"use client";

import { 
    LayoutDashboard, 
    TrendingUp, 
    TrendingDown, 
    ShieldCheck, 
    RefreshCw,
    Activity,
    PieChart,
    ChevronRight,
    BookOpen
} from "lucide-react";
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
    analysis: PortfolioAnalysisResponse | null;
    analyzeError?: string | null;
    analyzing: boolean;
    loading: boolean;
    loadingAnalysis: boolean;
    onAnalyze: () => Promise<void>;
    onSelectTicker: (ticker: string | null) => void;
    onShowReportChange: (show: boolean) => void;
    showReport: boolean;
    summary: PortfolioSummary | null;
}

export function PortfolioDashboard({
    analysis,
    analyzeError,
    analyzing,
    loading,
    loadingAnalysis,
    onAnalyze,
    onSelectTicker,
    onShowReportChange,
    showReport,
    summary,
}: PortfolioDashboardProps) {

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-canvas">
                <div className="flex flex-col items-center gap-4">
                    <RefreshCw className="h-8 w-8 text-ink animate-spin" />
                    <p className="text-sm font-medium text-ink-3">正在生成持仓透视...</p>
                </div>
            </div>
        );
    }

    const isProfit = (summary?.total_unrealized_pl || 0) >= 0;

    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-canvas custom-scrollbar">
            <div className="grid grid-cols-12 gap-4 max-w-7xl mx-auto">
                
                {/* Top Stats Banner */}
                <div className="col-span-12 lg:col-span-8 flex flex-col gap-4">
                    <div className="card rounded-lg p-6 border-line relative overflow-hidden">
                        
                        
                        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                            <div className="space-y-1">
                                <span className="text-[10px] font-bold text-ink-3 uppercase tracking-wide">总资产净值 (Total Equity)</span>
                                <div className="flex items-baseline gap-2">
                                    <h2 className="text-4xl font-bold tracking-tighter text-ink">
                                        ${summary?.total_market_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </h2>
                                    <span className="text-[10px] font-bold text-ink-3">USD</span>
                                </div>
                            </div>

                            <div className="flex gap-8">
                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-ink-3 uppercase tracking-wide">累计盈亏 (P/L)</span>
                                    <div className={clsx(
                                        "flex items-center gap-1.5 font-bold text-lg tabular-nums",
                                        isProfit ? "text-up" : "text-down"
                                    )}>
                                        {isProfit ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                                        {isProfit ? "+" : ""}{summary?.total_unrealized_pl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                    <div className={clsx(
                                        "text-[10px] font-bold px-2 py-0.5 rounded-full inline-block",
                                        isProfit ? "bg-up/10 text-up" : "bg-down/10 text-down"
                                    )}>
                                        {summary?.total_pl_percent.toFixed(2)}%
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <span className="text-[10px] font-bold text-ink-3 uppercase tracking-wide">今日变动 (Day Change)</span>
                                    <div className={clsx(
                                        "flex items-center gap-1.5 font-bold text-lg tabular-nums",
                                        (summary?.day_change || 0) >= 0 ? "text-up" : "text-down"
                                    )}>
                                        {(summary?.day_change || 0) >= 0 ? "+" : ""}{summary?.day_change.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Holdings Table */}
                    <div className="card rounded-lg border-line overflow-hidden">
                        <div className="px-5 py-3 border-b border-line flex items-center justify-between">
                            <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2">
                                <LayoutDashboard className="h-3.5 w-3.5 text-ink" />
                                资产持仓细节 (Holdings)
                            </h3>
                            <div className="text-[10px] text-ink-3 font-bold">
                                共 {summary?.holdings.length} 个标的
                            </div>
                        </div>
                        
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="bg-elevated/60 text-[10px] font-bold text-ink-3 tracking-tight">
                                        <th className="px-5 py-2.5">代码/名称</th>
                                        <th className="px-3 py-2.5 text-right">数量</th>
                                        <th className="px-3 py-2.5 text-right">成本</th>
                                        <th className="px-3 py-2.5 text-right">市价</th>
                                        <th className="px-3 py-2.5 text-right">市值</th>
                                        <th className="px-3 py-2.5 text-right">占比</th>
                                        <th className="px-3 py-2.5 text-right">盈亏</th>
                                        <th className="px-3 py-2.5 text-right">当前PE</th>
                                        <th className="px-3 py-2.5 text-right">远期PE</th>
                                        <th className="px-3 py-2.5 text-right">盈亏比</th>
                                        <th className="px-3 py-2.5 text-right" title="计划盈亏比 = 预期收益 / 预期风险">计划盈亏比</th>
                                        <th className="px-5 py-2.5 text-right"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-line">
                                    {summary?.holdings.map((item) => {
                                        const weight = (item.market_value / (summary?.total_market_value || 1)) * 100;
                                        return (
                                            <tr 
                                                key={item.ticker} 
                                                className="hover:bg-elevated transition-colors group cursor-pointer"
                                                onClick={() => onSelectTicker(item.ticker)}
                                            >
                                                <td className="px-5 py-3">
                                                    <div className="flex flex-col">
                                                        <span className="font-bold text-ink text-sm">{item.ticker}</span>
                                                        <span className="text-[10px] text-ink-3 truncate max-w-[100px]">{item.name}</span>
                                                    </div>
                                                </td>
                                                <td className="px-3 py-3 text-right font-medium text-xs tabular-nums text-ink-2 dark:text-ink-3">{item.quantity}</td>
                                                <td className="px-3 py-3 text-right font-medium text-xs tabular-nums text-ink-2 dark:text-ink-3">${item.avg_cost.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right font-medium text-xs tabular-nums text-ink-2 dark:text-ink-3">${item.current_price.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className="font-bold text-xs tabular-nums text-ink">${item.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className="font-bold text-xs tabular-nums text-ink">{weight.toFixed(1)}%</span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <div className="flex flex-col items-end">
                                                        <span className={clsx(
                                                            "font-bold text-xs tabular-nums",
                                                            item.unrealized_pl >= 0 ? "text-up" : "text-down"
                                                        )}>
                                                            {item.unrealized_pl >= 0 ? "+" : ""}{item.unrealized_pl.toFixed(2)}
                                                        </span>
                                                        <span className={clsx(
                                                            "text-[10px] font-bold",
                                                            item.pl_percent >= 0 ? "text-up/70" : "text-down/70"
                                                        )}>
                                                            {item.pl_percent.toFixed(2)}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className="text-[10px] font-bold tabular-nums text-ink-2 dark:text-ink-2">
                                                        {item.pe_ratio ? item.pe_ratio.toFixed(1) : "--"}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className="text-[10px] font-bold tabular-nums text-ink-3 dark:text-ink-3">
                                                        {item.forward_pe ? item.forward_pe.toFixed(1) : "--"}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className={clsx(
                                                        "text-[10px] font-bold tabular-nums",
                                                        (item.risk_reward_ratio || 0) >= 2.0 ? "text-up" :
                                                        (item.risk_reward_ratio || 0) >= 1.5 ? "text-ink" :
                                                        "text-down"
                                                    )}>
                                                        {item.risk_reward_ratio ? item.risk_reward_ratio.toFixed(2) : "--"}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className={clsx(
                                                        "text-[10px] font-bold tabular-nums",
                                                        (item.target_risk_reward_ratio || 0) >= 2.0 ? "text-up" :
                                                        (item.target_risk_reward_ratio || 0) >= 1.5 ? "text-ink" :
                                                        "text-ink-3"
                                                    )}>
                                                        {item.target_risk_reward_ratio ? item.target_risk_reward_ratio.toFixed(2) : "--"}
                                                    </span>
                                                </td>
                                                <td className="px-5 py-3 text-right opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <ChevronRight className="h-3 w-3 text-ink-3" />
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Sidebar: Sector + diagnosis */}
                <div className="col-span-12 lg:col-span-4 space-y-4">
                    
                    {/* Portfolio diagnosis card */}
                    <div className="card rounded-lg border-line p-5 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            
                        </div>
                        
                        <h3 className="text-ink font-semibold text-xs tracking-wide flex items-center gap-2 mb-4">
                            <Activity className="h-3.5 w-3.5 text-ink" />
                            组合诊断
                        </h3>

                        {(!analysis && loadingAnalysis) ? (
                            <div className="py-8 flex flex-col items-center justify-center gap-3 animate-pulse">
                                <div className="h-10 w-10 rounded-full bg-elevated border border-line flex items-center justify-center">
                                    <RefreshCw className="h-5 w-5 text-ink animate-spin" />
                                </div>
                                <p className="text-ink-3 text-[10px] font-bold">同步历史诊断...</p>
                            </div>
                        ) : !analysis ? (
                            <div className="py-6 flex flex-col items-center text-center gap-3">
                                <div className="w-12 h-12 rounded-full bg-elevated flex items-center justify-center border border-line">
                                    <ShieldCheck className="h-6 w-6 text-ink" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-ink-2 text-xs font-bold">查看组合风险概览</p>
                                    <p className="text-ink-3 text-[10px] px-4">审视组合风险、行业集中度并获得策略建议。</p>
                                </div>
                                {analyzeError && (
                                    <p className="text-down text-[10px] bg-down-soft border border-line rounded-lg px-3 py-2 w-full text-left leading-relaxed">
                                        ⚠ {analyzeError}
                                    </p>
                                )}
                                <Button 
                                    onClick={onAnalyze} 
                                    disabled={analyzing}
                                    className="w-full bg-ink hover:opacity-90 text-canvas font-medium rounded-md mt-2 h-9 text-xs"
                                >
                                    {analyzing ? (
                                        <>
                                            <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
                                            分析中...
                                        </>
                                    ) : "生成组合诊断"}
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                                <div className="flex items-center gap-3">
                                    <div className="relative flex items-center justify-center">
                                        <svg className="h-12 w-12 -rotate-90">
                                            <circle 
                                                cx="24" cy="24" r="20" 
                                                className="stroke-line-strong fill-none" 
                                                strokeWidth="4"
                                            />
                                            <circle 
                                                cx="24" cy="24" r="20" 
                                                className="stroke-ink fill-none transition-all duration-1000" 
                                                strokeWidth="4"
                                                strokeDasharray={125}
                                                strokeDashoffset={125 - (125 * (analysis.health_score || 0)) / 100}
                                            />
                                        </svg>
                                        <span className="absolute text-sm font-bold text-white">{analysis.health_score}</span>
                                    </div>
                                    <div className="min-w-0">
                                        <span className={clsx(
                                            "inline-block px-1.5 py-0.5 rounded-full text-[8px] font-bold tracking-tight mb-1",
                                            analysis.risk_level === "低" ? "bg-up-soft text-up" :
                                            analysis.risk_level === "中" ? "bg-elevated text-ink-2" :
                                            "bg-down-soft text-down"
                                        )}>
                                            风险: {analysis.risk_level}
                                        </span>
                                        <p className="text-white font-bold text-xs leading-tight truncate">{analysis.summary}</p>
                                    </div>
                                </div>

                                <div className="bg-elevated rounded-xl p-3 border border-line">
                                    <p className="text-ink-2 text-[11px] leading-relaxed line-clamp-3">
                                        {analysis.strategic_advice}
                                    </p>
                                </div>

                                <div className="flex gap-2">
                                    <Dialog open={showReport} onOpenChange={onShowReportChange}>
                                        <DialogTrigger asChild>
                                            <Button 
                                                variant="secondary"
                                                className="flex-1 bg-ink text-canvas hover:opacity-90 font-bold rounded-xl h-9 text-[10px] gap-1.5"
                                            >
                                                <BookOpen className="h-3 w-3" />
                                                深度报告
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent className="max-w-2xl bg-white dark:bg-neutral-900 border-line p-0 overflow-hidden rounded-2xl">
                                            <DialogHeader className="p-5 border-b border-line flex flex-row items-center justify-between bg-elevated/60 space-y-0 text-left">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-xl bg-elevated flex items-center justify-center border border-line">
                                                        <Activity className="h-4 w-4 text-ink" />
                                                    </div>
                                                    <div className="text-left">
                                                        <DialogTitle className="font-bold text-base text-ink leading-tight">
                                                            组合诊断报告
                                                        </DialogTitle>
                                                        <DialogDescription className="text-[10px] text-ink-3 font-bold uppercase tracking-wide">
                                                            Portfolio Deep Insight Report
                                                        </DialogDescription>
                                                    </div>
                                                </div>
                                            </DialogHeader>
                                            
                                            <ScrollArea className="h-[50vh] p-6">
                                                <div className="prose prose-slate dark:prose-invert max-w-none text-xs prose-p:text-ink-2 dark:prose-p:text-ink-3 prose-headings:text-ink dark:prose-headings:text-white prose-strong:text-ink dark:prose-strong:text-white">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.detailed_report}</ReactMarkdown>
                                                </div>
                                            </ScrollArea>
                                            
                                            <div className="p-3 bg-elevated border-t border-line flex justify-between items-center text-[10px]">
                                                <span className="font-bold text-ink-3">报告生成时间: {new Date(analysis.created_at).toLocaleString()}</span>
                                                <Button variant="ghost" size="sm" onClick={() => onShowReportChange(false)} className="font-bold text-[10px] h-7">关闭</Button>
                                            </div>
                                        </DialogContent>
                                    </Dialog>

                                    <Button 
                                        variant="outline" 
                                        onClick={onAnalyze}
                                        disabled={analyzing}
                                        className="bg-transparent border-neutral-700 hover:bg-neutral-800 text-ink-3 font-bold rounded-xl h-9 px-2.5"
                                    >
                                        <RefreshCw className={clsx("h-3 w-3", analyzing && "animate-spin")} />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Sector Exposure Chart */}
                    <div className="card rounded-lg p-5 border-line">
                        <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-2 mb-4">
                            <PieChart className="h-3.5 w-3.5 text-up" />
                            行业覆盖 / 分布
                        </h3>
                        
                        <div className="space-y-4">
                            {summary?.sector_exposure.sort((a, b) => b.value - a.value).map((s, idx) => (
                                <div key={idx} className="space-y-1">
                                    <div className="flex justify-between text-[10px] font-bold tracking-tight">
                                        <span className="text-ink-3 dark:text-ink-3">{s.sector === "Unknown" ? "未归类/其他" : s.sector}</span>
                                        <span className="text-ink">{s.weight.toFixed(1)}%</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-elevated rounded-full overflow-hidden">
                                        <div 
                                            className={clsx(
                                                "h-full rounded-full transition-all duration-700",
                                                idx === 0 ? "bg-ink" :
                                                idx === 1 ? "bg-ink/60" :
                                                idx === 2 ? "bg-ink/40" : "bg-ink/25"
                                            )} 
                                            style={{ width: `${s.weight}%` }} 
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6 p-3 bg-elevated rounded-xl border border-line text-center">
                            <p className="text-[10px] text-ink-3 font-bold">
                                建议：避免行业集中度超过 40% 以降低系统风险。
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
