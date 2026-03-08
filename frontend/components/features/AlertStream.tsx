import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Bell, Zap, TrendingUp, AlertTriangle, Calendar, Clock, ChevronRight } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useAuth } from '@/context/AuthContext';
import { formatDateTime } from '@/lib/utils';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface NotificationLog {
    id: string;
    type: string;
    title: string;
    content: string;
    card_payload: any;
    created_at: string;
}

const AlertStream: React.FC = () => {
    const { isAuthenticated, user } = useAuth();
    const [logs, setLogs] = useState<NotificationLog[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchHistory = async () => {
        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await axios.get(`${apiBase}/api/notifications/history?limit=30`);
            setLogs(response.data);
        } catch (error) {
            console.error("Failed to fetch notification history:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
        // 每 30 秒自动刷新一次，确保持时效性
        const timer = setInterval(fetchHistory, 30000);
        return () => clearInterval(timer);
    }, []);

    const getIcon = (type: string) => {
        switch (type) {
            case 'MACRO_ALERT': return <Zap className="w-5 h-5 text-amber-500" />;
            case 'PRICE_ALERT': return <TrendingUp className="w-5 h-5 text-emerald-600" />;
            case 'DAILY_REPORT': return <Calendar className="w-5 h-5 text-blue-600" />;
            default: return <Bell className="w-5 h-5 text-slate-400" />;
        }
    };

    const getTypeLabel = (type: string) => {
        switch (type) {
            case 'MACRO_ALERT': return '宏观雷达';
            case 'PRICE_ALERT': return '价格监控';
            case 'DAILY_REPORT': return '每日体检';
            case 'INDICATOR_ALERT': return '指标告警';
            default: return '系统通知';
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 animate-pulse">
                <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
                <div className="h-4 w-40 bg-slate-200 rounded"></div>
            </div>
        );
    }

    if (logs.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
                <Bell className="w-16 h-16 mb-4 opacity-20" />
                <p>暂无推送历史，系统探针正在持续工作中...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto py-4">
            <div className="flex items-center justify-between px-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                    <Zap className="w-6 h-6 text-amber-500 fill-amber-500" />
                    智能提醒流 (Smart Alert Stream)
                </h2>
                <span className="text-xs text-slate-400 bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded-full">
                    实时同步已开启
                </span>
            </div>

            <div className="relative border-l-2 border-slate-100 dark:border-zinc-800 ml-8 px-6 space-y-8">
                {logs.map((log) => (
                    <div key={log.id} className="relative group">
                        {/* 时间线圆点 */}
                        <div className={cn(
                            "absolute -left-[33px] top-1 w-4 h-4 rounded-full border-2 border-white dark:border-zinc-950 shadow-sm z-10",
                            log.type === 'MACRO_ALERT' ? 'bg-amber-500' : 
                            log.type === 'PRICE_ALERT' ? 'bg-emerald-600' : 'bg-blue-600'
                        )} />

                        <div className="bg-white dark:bg-zinc-900/50 rounded-xl border border-slate-100 dark:border-zinc-800 p-5 shadow-sm hover:shadow-md transition-all group-hover:border-slate-300 dark:group-hover:border-zinc-700">
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-slate-50 dark:bg-zinc-800/50 rounded-lg">
                                        {getIcon(log.type)}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                                                {getTypeLabel(log.type)}
                                            </span>
                                            <span className="text-xs text-slate-400 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {formatDateTime(log.created_at, user?.timezone || "Asia/Shanghai")}
                                            </span>
                                        </div>
                                        <h3 className="text-lg font-bold text-slate-900 dark:text-zinc-100 mt-0.5 leading-snug">
                                            {log.title}
                                        </h3>
                                    </div>
                                </div>
                            </div>
                            
                            <p className="text-slate-600 dark:text-zinc-400 text-sm leading-relaxed whitespace-pre-wrap">
                                {log.content}
                            </p>

                            <div className="mt-4 pt-4 border-t border-dotted border-slate-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-slate-400">
                                <span className="flex items-center gap-1">
                                    渠道: <strong className="text-slate-500 dark:text-zinc-300">飞书机器人 (Webhook)</strong>
                                </span>
                                <button className="flex items-center gap-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium group/btn">
                                    查看完整卡片 <ChevronRight className="w-3 h-3 transition-transform group-hover/btn:translate-x-0.5" />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AlertStream;
