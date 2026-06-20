import { Calendar, TrendingDown, TrendingUp, Minus } from "lucide-react";
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
    company_event: "公司事件",
};

const TYPE_COLORS: Record<string, string> = {
    earnings: "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-600/10 dark:text-rose-400 dark:border-rose-600/20",
    fomc: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-600/10 dark:text-amber-400 dark:border-amber-600/20",
    product: "bg-violet-50 text-violet-600 border-violet-200 dark:bg-violet-600/10 dark:text-violet-400 dark:border-violet-600/20",
    macro: "bg-neutral-50 text-neutral-600 border-neutral-200 dark:bg-neutral-700/20 dark:text-neutral-300 dark:border-neutral-700",
    technical: "bg-cyan-50 text-cyan-600 border-cyan-200 dark:bg-cyan-600/10 dark:text-cyan-400 dark:border-cyan-600/20",
    company_event: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-600/10 dark:text-blue-400 dark:border-blue-600/20",
};

const IMPACT_CONFIG = {
    bullish: { icon: TrendingUp, color: "text-emerald-500" },
    bearish: { icon: TrendingDown, color: "text-rose-500" },
    neutral: { icon: Minus, color: "text-neutral-400" },
} as const;

const IMPACT_LEVEL_CONFIG = {
    high: {
        dot: "bg-rose-500 border-rose-500 ring-4 ring-rose-500/15",
        text: "text-rose-600 dark:text-rose-400",
        tag: "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-600/10 dark:text-rose-400 dark:border-rose-600/20",
        card: "bg-rose-50/40 border-rose-100 dark:bg-rose-600/5 dark:border-rose-600/15",
        label: "高影响",
    },
    medium: {
        dot: "bg-amber-500 border-amber-500",
        text: "text-amber-600 dark:text-amber-400",
        tag: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-600/10 dark:text-amber-400 dark:border-amber-600/20",
        card: "bg-amber-50/40 border-amber-100 dark:bg-amber-600/5 dark:border-amber-600/15",
        label: "中影响",
    },
    low: {
        dot: "bg-neutral-400 border-neutral-400",
        text: "text-neutral-500 dark:text-neutral-400",
        tag: "bg-neutral-50 text-neutral-600 border-neutral-200 dark:bg-neutral-700/20 dark:text-neutral-300 dark:border-neutral-700",
        card: "bg-neutral-50/60 border-neutral-100 dark:bg-neutral-800/40 dark:border-neutral-700/60",
        label: "低影响",
    },
} as const;

function parseDate(dateStr: string): Date | null {
    if (!dateStr || dateStr === "未知") return null;
    const parsed = new Date(dateStr);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getDaysAway(dateStr: string): number | null {
    const parsed = parseDate(dateStr);
    if (!parsed) return null;
    const diff = Math.ceil((parsed.getTime() - Date.now()) / 86400000);
    return diff;
}

function formatDate(dateStr: string): string {
    const parsed = parseDate(dateStr);
    if (!parsed) return "待定";
    return parsed.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function clampPosition(daysAway: number | null): number {
    if (daysAway == null) return 100;
    const clamped = Math.max(0, Math.min(30, daysAway));
    return (clamped / 30) * 100;
}

export function CatalystTimeline({ catalysts }: CatalystTimelineProps) {
    if (!catalysts || catalysts.length === 0) return null;

    const sorted = [...catalysts].sort((a, b) => {
        const aDate = parseDate(a.date);
        const bDate = parseDate(b.date);
        if (!aDate) return 1;
        if (!bDate) return -1;
        return aDate.getTime() - bDate.getTime();
    });

    const timelineItems = sorted.slice(0, 4);
    const focusIndex = timelineItems.findIndex((item) => item.impact_level === "high");
    const highlightedIndex = focusIndex >= 0 ? focusIndex : 0;

    return (
        <div className="bg-white dark:bg-zinc-900 border border-neutral-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-3 border-b border-neutral-100 dark:border-zinc-800 flex items-center gap-2">
                <Calendar className="h-4 w-4 text-amber-600" strokeWidth={2} />
                <span className="text-[11px] font-black text-neutral-700 dark:text-neutral-300 uppercase tracking-wider">
                    催化剂时间轴
                </span>
                <span className="text-[10px] text-neutral-400 ml-1">— 未来30天内可能影响判断的关键事件</span>
            </div>

            <div className="p-6">
                <div className="relative pt-2 pb-4 mb-5">
                    <div className="relative h-4 mb-2">
                        {[0, 7, 14, 21, 30].map((day) => (
                            <div
                                key={day}
                                className="absolute -tranneutral-x-1/2"
                                style={{ left: `${(day / 30) * 100}%` }}
                            >
                                <span className="text-[9px] font-medium text-neutral-400 mono">
                                    {day === 0 ? "D+0" : `D+${day}`}
                                </span>
                            </div>
                        ))}
                    </div>

                    <div className="relative h-16">
                        <div className="absolute left-0 right-0 top-1/2 -tranneutral-y-1/2 h-px bg-neutral-200 dark:bg-zinc-700" />
                        {[0, 7, 14, 21, 30].map((day) => (
                            <div
                                key={day}
                                className="absolute top-1/2 -tranneutral-y-1/2 w-px h-1.5 bg-neutral-300 dark:bg-zinc-600"
                                style={{ left: `${(day / 30) * 100}%` }}
                            />
                        ))}

                        {timelineItems.map((catalyst, idx) => {
                            const daysAway = getDaysAway(catalyst.date);
                            const impactLevel = IMPACT_LEVEL_CONFIG[
                                (catalyst.impact_level as keyof typeof IMPACT_LEVEL_CONFIG) || "medium"
                            ];
                            const ImpactIcon = IMPACT_CONFIG[
                                (catalyst.impact as keyof typeof IMPACT_CONFIG) || "neutral"
                            ].icon;
                            const impactColor = IMPACT_CONFIG[
                                (catalyst.impact as keyof typeof IMPACT_CONFIG) || "neutral"
                            ].color;
                            const isFocus = idx === highlightedIndex;

                            return (
                                <div
                                    key={`${catalyst.event}-${idx}`}
                                    className="absolute top-1/2 -tranneutral-y-1/2 -tranneutral-x-1/2 z-10"
                                    style={{ left: `${clampPosition(daysAway)}%` }}
                                >
                                    <div className="flex flex-col items-center">
                                        {isFocus && (
                                            <div className="absolute bottom-full mb-2 flex flex-col items-center">
                                                <span className="bg-rose-500 text-white text-[9px] font-black px-2 py-0.5 rounded-full whitespace-nowrap shadow-lg">
                                                    焦点事件
                                                </span>
                                                <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-t-[4px] border-l-transparent border-r-transparent border-t-rose-500 -mt-px" />
                                            </div>
                                        )}
                                        <div className={clsx(
                                            "rounded-full border-2 border-white dark:border-zinc-900 shadow-sm",
                                            isFocus ? "w-5 h-5" : "w-3.5 h-3.5",
                                            impactLevel.dot,
                                        )} />
                                        <div className="mt-1.5 text-center">
                                            <div className="text-[10px] font-bold text-neutral-900 dark:text-neutral-200 leading-tight whitespace-nowrap">
                                                {catalyst.event}
                                            </div>
                                            <div className={clsx("text-[9px] mono font-bold", impactLevel.text)}>
                                                {daysAway == null ? "待定" : daysAway < 0 ? "已过" : `D+${daysAway}`}
                                            </div>
                                        </div>
                                        <ImpactIcon className={clsx("h-3 w-3 mt-1", impactColor)} strokeWidth={2.5} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {sorted.map((catalyst, idx) => {
                        const impactLevel = IMPACT_LEVEL_CONFIG[
                            (catalyst.impact_level as keyof typeof IMPACT_LEVEL_CONFIG) || "medium"
                        ];
                        const typeColor = TYPE_COLORS[catalyst.type] ?? TYPE_COLORS.macro;
                        const typeLabel = TYPE_LABELS[catalyst.type] ?? catalyst.type;
                        const daysAway = getDaysAway(catalyst.date);
                        const isFocus = idx === highlightedIndex;
                        const isWide = isFocus || idx === sorted.length - 1;

                        return (
                            <div
                                key={`${catalyst.event}-card-${idx}`}
                                className={clsx(
                                    "rounded-xl px-4 py-3 border",
                                    impactLevel.card,
                                    isWide && "md:col-span-2",
                                )}
                            >
                                <div className="flex items-start gap-3">
                                    <div className={clsx("w-2 h-2 rounded-full mt-1.5 shrink-0", impactLevel.dot.split(" ")[0])} />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap mb-1">
                                            <span className="font-bold text-sm text-neutral-900 dark:text-neutral-200">
                                                {catalyst.event}
                                            </span>
                                            <span className={clsx("text-[9px] font-black px-1.5 py-0.5 rounded border", impactLevel.tag)}>
                                                {impactLevel.label}
                                            </span>
                                            <span className={clsx("text-[9px] font-black px-1.5 py-0.5 rounded border", typeColor)}>
                                                {typeLabel}
                                            </span>
                                            <span className="ml-auto text-[10px] mono text-neutral-500 dark:text-neutral-400">
                                                {formatDate(catalyst.date)} · {daysAway == null ? "待定" : daysAway < 0 ? "已过" : `D+${daysAway}`}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-neutral-600 dark:text-neutral-400 leading-relaxed">
                                            {catalyst.description || "暂无补充说明"}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
