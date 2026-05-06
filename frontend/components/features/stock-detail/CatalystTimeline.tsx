
import { TrendingUp, TrendingDown, Minus, Calendar, Zap } from "lucide-react";
import clsx from "clsx";

interface Catalyst {
    date: string;
    event: string;
    type: string;
    impact: string;
    description: string;
    impact_level?: string;
}

interface CatalystTimelineProps {
    catalysts?: Catalyst[];
}

const TYPE_LABELS: Record<string, string> = {
    earnings: "财报",
    fomc: "FOMC",
    product: "产品",
    macro: "宏观",
    technical: "技术",
};

const TYPE_COLORS: Record<string, string> = {
    earnings: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800",
    fomc: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800",
    product: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800",
    macro: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700",
    technical: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-200 dark:border-cyan-800",
};

const IMPACT_CONFIG = {
    bullish: { icon: TrendingUp, color: "text-emerald-500", dotColor: "bg-emerald-500", lineColor: "border-emerald-200 dark:border-emerald-900" },
    bearish: { icon: TrendingDown, color: "text-red-500", dotColor: "bg-red-500", lineColor: "border-red-200 dark:border-red-900" },
    neutral: { icon: Minus, color: "text-slate-400", dotColor: "bg-slate-400", lineColor: "border-slate-200 dark:border-slate-700" },
};

const IMPACT_LEVEL_CONFIG = {
    high: { dotColor: "border-rose-400", dotFill: "bg-rose-500", textColor: "text-rose-600", bgTag: "bg-rose-500/10 text-rose-600 border-rose-200 dark:border-rose-900" },
    medium: { dotColor: "border-amber-400", dotFill: "bg-amber-500", textColor: "text-amber-600", bgTag: "bg-amber-500/10 text-amber-600 border-amber-200 dark:border-amber-900" },
    low: { dotColor: "border-slate-300", dotFill: "bg-slate-400", textColor: "text-slate-500", bgTag: "bg-slate-500/10 text-slate-500 border-slate-200 dark:border-slate-700" },
};

function formatDate(dateStr: string): string {
    if (dateStr === "未知" || !dateStr) return "待定";
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
    } catch {
        return dateStr;
    }
}

function getDaysAway(dateStr: string): string | null {
    if (dateStr === "未知" || !dateStr) return null;
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return null;
        const diff = Math.ceil((d.getTime() - Date.now()) / 86400000);
        if (diff < 0) return "已过";
        if (diff === 0) return "今日";
        return `${diff}天`;
    } catch {
        return null;
    }
}

export function CatalystTimeline({ catalysts }: CatalystTimelineProps) {
    if (!catalysts || catalysts.length === 0) return null;

    const sorted = [...catalysts].sort((a, b) => {
        if (a.date === "未知") return 1;
        if (b.date === "未知") return -1;
        return new Date(a.date).getTime() - new Date(b.date).getTime();
    });

    return (
        <div className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-2xl p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5 text-amber-600" strokeWidth={2.5} />
                <h3 className="text-xs font-black text-slate-700 dark:text-slate-300 uppercase tracking-widest">
                    催化剂时间轴
                </h3>
                <span className="text-[10px] text-slate-400">— 未来30天内可能影响判断的关键事件</span>
            </div>

            {/* Timeline */}
            <div className="relative">
                {/* Vertical line */}
                <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-100 dark:bg-zinc-800" />

                <div className="space-y-4">
                    {sorted.map((catalyst, idx) => {
                        const impact = IMPACT_CONFIG[catalyst.impact as keyof typeof IMPACT_CONFIG] ?? IMPACT_CONFIG.neutral;
                        const ImpactIcon = impact.icon;
                        const daysAway = getDaysAway(catalyst.date);
                        const typeLabel = TYPE_LABELS[catalyst.type] ?? catalyst.type;
                        const typeColor = TYPE_COLORS[catalyst.type] ?? TYPE_COLORS.macro;

                        // Impact level colors
                        const impactLevelKey = catalyst.impact_level as keyof typeof IMPACT_LEVEL_CONFIG | undefined;
                        const levelConfig = impactLevelKey ? IMPACT_LEVEL_CONFIG[impactLevelKey] : null;

                        return (
                            <div key={idx} className="flex items-start gap-4 relative">
                                {/* Timeline dot */}
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 z-10 ${levelConfig ? `bg-slate-100 dark:bg-zinc-800 border-2 ${levelConfig.dotColor}` : `${impact.dotColor} border-2 border-white dark:border-zinc-900`}`}>
                                    <div className={`w-2 h-2 rounded-full ${levelConfig ? levelConfig.dotFill : impact.dotColor}`} />
                                </div>

                                {/* Content */}
                                <div className="flex-1 pb-1">
                                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                                        <span className="font-bold text-sm text-slate-900 dark:text-slate-200">
                                            {catalyst.event}
                                        </span>
                                        {levelConfig && (
                                            <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${levelConfig.bgTag}`}>
                                                {catalyst.impact_level === "high" ? "高影响" : catalyst.impact_level === "medium" ? "中影响" : "低影响"}
                                            </span>
                                        )}
                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded border ${typeColor}`}>
                                            {typeLabel}
                                        </span>
                                        <ImpactIcon className={`h-3 w-3 ${impact.color}`} strokeWidth={2.5} />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                        距今 <span className={clsx("font-bold", levelConfig?.textColor ?? impact.color)}>{daysAway ?? "待定"}</span> · {formatDate(catalyst.date)}
                                        {catalyst.description && ` · ${catalyst.description}`}
                                    </p>
                                </div>

                                {/* Countdown column */}
                                {daysAway && daysAway !== "已过" && (
                                    <div className="shrink-0 text-right">
                                        <div className="text-[10px] text-slate-400">倒计时</div>
                                        <div className={`text-lg font-black mono ${levelConfig?.textColor ?? impact.color}`}>
                                            {daysAway.replace("天", "d")}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Empty hint */}
            {sorted.length === 0 && (
                <div className="flex items-center gap-2 text-slate-300 dark:text-slate-600 py-2">
                    <Zap className="h-4 w-4" />
                    <span className="text-xs">暂无已识别催化剂</span>
                </div>
            )}
        </div>
    );
}
