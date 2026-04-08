"use client";

import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface Assumption {
    assumption: string;
    breakpoint: string;
}

interface KeyAssumptionsProps {
    assumptions?: Assumption[];
}

export function KeyAssumptions({ assumptions }: KeyAssumptionsProps) {
    const [expanded, setExpanded] = useState<number | null>(null);

    if (!assumptions || assumptions.length === 0) return null;

    return (
        <div className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-2xl p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" strokeWidth={2.5} />
                <h3 className="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                    关键假设 &amp; 断点
                </h3>
            </div>

            {/* Assumption list */}
            <div className="space-y-2">
                {assumptions.map((item, idx) => {
                    const isOpen = expanded === idx;
                    return (
                        <div
                            key={idx}
                            className="border border-slate-100 dark:border-zinc-800 rounded-xl overflow-hidden"
                        >
                            {/* Assumption row */}
                            <button
                                className="w-full flex items-start justify-between gap-3 p-3 text-left hover:bg-slate-50 dark:hover:bg-zinc-800/60 transition-colors"
                                onClick={() => setExpanded(isOpen ? null : idx)}
                            >
                                <div className="flex items-start gap-2 min-w-0">
                                    <span className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full bg-slate-100 dark:bg-zinc-800 text-[9px] font-black text-slate-500 dark:text-slate-400 flex items-center justify-center">
                                        {idx + 1}
                                    </span>
                                    <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-200 leading-snug">
                                        {item.assumption}
                                    </span>
                                </div>
                                {isOpen ? (
                                    <ChevronUp className="flex-shrink-0 h-3.5 w-3.5 text-slate-400 mt-0.5" />
                                ) : (
                                    <ChevronDown className="flex-shrink-0 h-3.5 w-3.5 text-slate-400 mt-0.5" />
                                )}
                            </button>

                            {/* Breakpoint (collapsible) */}
                            {isOpen && (
                                <div className="px-3 pb-3 pt-0">
                                    <div className="flex items-start gap-2 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/40 rounded-lg p-2.5">
                                        <AlertTriangle className="flex-shrink-0 h-3 w-3 text-red-400 mt-0.5" strokeWidth={2.5} />
                                        <div>
                                            <p className="text-[9px] font-black text-red-400 uppercase tracking-wider mb-0.5">
                                                假设失效条件
                                            </p>
                                            <p className="text-[11px] text-red-600 dark:text-red-400 leading-snug">
                                                {item.breakpoint}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
