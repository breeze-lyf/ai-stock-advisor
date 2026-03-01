"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TrendingUp, TrendingDown, AlertCircle, RefreshCw, Globe, ArrowRight } from "lucide-react";
import clsx from "clsx";
import { getMacroRadar } from "@/lib/api";

import { GlobalNewsFeed } from "./GlobalNewsFeed";

interface MacroTopic {
  id: string;
  title: string;
  summary: string;
  heat_score: number;
  impact_analysis: {
    logic: string;
    beneficiaries: { ticker: string; reason: string }[];
    detriments: { ticker: string; reason: string }[];
  };
  source_links: string[];
  updated_at: string;
}

interface HotspotRadarProps {
  onSelectTicker: (ticker: string) => void;
}

export function HotspotRadar({ onSelectTicker }: HotspotRadarProps) {
  const [topics, setTopics] = useState<MacroTopic[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchRadar = async (refresh = false) => {
    setLoading(true);
    try {
      const data = await getMacroRadar(refresh);
      setTopics(data);
    } catch (error) {
      console.error("Failed to fetch macro radar", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRadar();
  }, []);

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-950 p-4 space-y-4">
      <div className="shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Globe className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 italic">全球宏观雷达 <span className="text-xs font-normal text-slate-400 ml-1">Market Pulse</span></h2>
            <p className="text-[11px] text-slate-500 font-medium">AI 实时监测市场重大热点与板块轮动逻辑</p>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => fetchRadar(true)} 
          disabled={loading}
          className="gap-2 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800"
        >
          <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
          全网扫描热点
        </Button>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-12 gap-4">
        {/* Left Column: Real-time News Feed */}
        {/*
## 全球资讯流：持久化与滚动修复 (Persistence & UI Fix)

针对您反馈的“热点不持久”及“页面无法滑动”问题，已完成深度优化：

### 1. 自动化持久化：不再需要手动点击
- **静默后台更新**：系统现已支持使用后端配置的 AI 密钥。当您进入页面时，若发现数据过旧，系统会自动在后台触发 AI 扫描，并在 30 秒内静默推送到前端，无需手动点击“全网扫描”。
- **定时任务调度**：集成到 `scheduler.py`，每 4 小时例行强制扫描一次全球热点，确保您任何时候打开都是“热”的数据。

### 2. UI 交互：恢复丝滑滚动
- **布局重构**：修复了 `HotspotRadar` 中由于 `h-full` 冲突导致的滚动锁定。采用 `flex-1 min-h-0` 方案，确保资讯流（左）与热点卡片（右）均能独立、顺畅地监听鼠标滚动。

## 验证结论 (Validation Results)
- **数据自动可见**：空数据/过期数据场景下，进入页面自动触发更新逻辑。
- **操作流畅度**：长列表滑动无卡顿，双栏布局适配完美。
        */}
        <div className="col-span-12 lg:col-span-3 flex flex-col min-h-0 overflow-hidden">
          <GlobalNewsFeed />
        </div>

        {/* Right Column: Macro Topics */}
        <div className="col-span-12 lg:col-span-9 h-full overflow-y-auto custom-scrollbar pr-1">
          <div className="space-y-4 max-w-5xl mx-auto pb-8">
            {topics.length === 0 && !loading && (
              <div className="text-center py-20 bg-white dark:bg-slate-900 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800">
                <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">暂无捕捉到的热点题材，请点击上方“全网扫描”</p>
              </div>
            )}

            {topics.map((topic) => (
              <Card key={topic.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow bg-white dark:bg-slate-900 rounded-2xl">
                <CardHeader className="pb-2 border-b border-slate-50 dark:border-slate-800/50">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg font-bold flex items-center gap-2">
                           {topic.title}
                        </CardTitle>
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <span>热度指数</span>
                          <div className="w-24 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                             <div 
                              className="h-full bg-rose-500" 
                              style={{ width: `${topic.heat_score}%` }}
                             />
                          </div>
                          <span className="font-mono text-rose-600 font-bold">{topic.heat_score}%</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-slate-400 uppercase tracking-widest font-medium">
                        Updated: {
                          new Date(topic.updated_at.endsWith('Z') ? topic.updated_at : topic.updated_at + 'Z').toLocaleString("zh-CN", {
                            timeZone: "Asia/Shanghai",
                            hour12: false,
                            year: 'numeric',
                            month: 'numeric',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: 'numeric',
                            second: 'numeric'
                          })
                        }
                      </span>
                    </div>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  <div className="p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800/50">
                    <h4 className="text-[10px] font-bold text-slate-400 mb-1 flex items-center gap-1 uppercase tracking-tight">
                      <RefreshCw className="w-2.5 h-2.5" /> AI 逻辑传导链
                    </h4>
                    <p className="text-[13px] text-slate-600 dark:text-slate-300 leading-relaxed">
                      {topic.impact_analysis?.logic || "AI 正在分析传导逻辑..."}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Beneficiaries */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-emerald-600 flex items-center gap-1 px-1">
                        <TrendingUp className="w-3 h-3" /> 利好板块/标的
                      </h4>
                      <div className="space-y-2">
                        {(topic.impact_analysis?.beneficiaries || []).map((item, idx) => (
                          <div key={idx} className="group p-3 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100/50 dark:border-emerald-900/30 rounded-xl flex items-center justify-between">
                            <div className="min-w-0">
                              <span 
                                onClick={() => onSelectTicker(item.ticker)}
                                className="text-sm font-bold text-emerald-700 dark:text-emerald-400 cursor-pointer hover:underline flex items-center gap-1"
                              >
                                ${item.ticker} <ArrowRight className="w-3 h-3 inline opacity-0 group-hover:opacity-100 transition-opacity" />
                              </span>
                              <p className="text-xs text-emerald-600/80 dark:text-emerald-500/80 truncate">{item.reason}</p>
                            </div>
                            <div className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
                              <TrendingUp className="w-3 h-3 text-emerald-600" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Detriments */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-rose-600 flex items-center gap-1 px-1">
                        <TrendingDown className="w-3 h-3" /> 利空板块/标的
                      </h4>
                      <div className="space-y-2">
                        {(topic.impact_analysis?.detriments || []).map((item, idx) => (
                          <div key={idx} className="group p-3 bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100/50 dark:border-rose-900/30 rounded-xl flex items-center justify-between">
                            <div className="min-w-0">
                               <span 
                                onClick={() => onSelectTicker(item.ticker)}
                                className="text-sm font-bold text-rose-700 dark:text-rose-400 cursor-pointer hover:underline flex items-center gap-1"
                              >
                                ${item.ticker} <ArrowRight className="w-3 h-3 inline opacity-0 group-hover:opacity-100 transition-opacity" />
                              </span>
                              <p className="text-xs text-rose-600/80 dark:text-rose-500/80 truncate">{item.reason}</p>
                            </div>
                            <div className="w-6 h-6 rounded-full bg-rose-100 dark:bg-rose-900/40 flex items-center justify-center">
                              <TrendingDown className="w-3 h-3 text-rose-600" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Button (Reuse components in same file for brevity)
function Button({ className, variant, size, children, ...props }: any) {
  const variants: any = {
    outline: "border border-slate-200 bg-white hover:bg-slate-100 text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:hover:bg-slate-800 dark:text-slate-100"
  };
  const sizes: any = {
    sm: "h-9 px-3 text-xs"
  };
  return (
    <button className={clsx("inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:opacity-50", variants[variant], sizes[size], className)} {...props}>
      {children}
    </button>
  );
}
