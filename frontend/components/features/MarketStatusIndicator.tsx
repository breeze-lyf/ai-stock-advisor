"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";

export function MarketStatusIndicator() {
    const [marketStatus, setMarketStatus] = useState<{
        status: 'open' | 'closed',
        text: string,
        countdown: string
    }>({ status: 'closed', text: 'Market Closed', countdown: '' });

    useEffect(() => {
        const calculateMarketStatus = () => {
            const now = new Date();
            // Get New York Time
            const nyTimeStr = now.toLocaleString("en-US", { timeZone: "America/New_York" });
            const nyDate = new Date(nyTimeStr);

            const day = nyDate.getDay(); // 0 = Sun, 6 = Sat
            const hours = nyDate.getHours();
            const minutes = nyDate.getMinutes();
            const timeInMinutes = hours * 60 + minutes;

            const openTime = 9 * 60 + 30; // 9:30 AM
            const closeTime = 16 * 60;    // 4:00 PM

            const isWeekend = day === 0 || day === 6;
            const isOpen = !isWeekend && timeInMinutes >= openTime && timeInMinutes < closeTime;

            let text = "";
            let countdown = "";
            let status: 'open' | 'closed' = isOpen ? 'open' : 'closed';

            if (isOpen) {
                text = "美股盘中 (OPEN)";
                const diff = closeTime - timeInMinutes;
                countdown = `距收盘: ${Math.floor(diff / 60)}h ${diff % 60}m`;
            } else {
                text = "美股休市 (CLOSED)";
                let diffMinutes = 0;

                if (isWeekend || timeInMinutes >= closeTime) {
                    const daysToWait = day === 5 ? 3 : day === 6 ? 2 : day === 0 ? 1 : (timeInMinutes >= closeTime ? 1 : 0);
                    const nextOpen = new Date(nyDate);
                    nextOpen.setDate(nyDate.getDate() + daysToWait);
                    nextOpen.setHours(9, 30, 0, 0);
                    diffMinutes = Math.floor((nextOpen.getTime() - nyDate.getTime()) / 60000);
                } else {
                    diffMinutes = openTime - timeInMinutes;
                }

                const h = Math.floor(diffMinutes / 60);
                const m = diffMinutes % 60;
                countdown = `距开盘: ${h}h ${m}m`;
            }

            setMarketStatus({ status, text, countdown });
        };

        calculateMarketStatus();
        const interval = setInterval(calculateMarketStatus, 60000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-50 dark:bg-slate-800/50 rounded-full border border-slate-100 dark:border-slate-800">
            <div className={clsx(
                "h-2 w-2 rounded-full animate-pulse",
                marketStatus.status === 'open' ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-red-500"
            )} />
            <div className="flex flex-col leading-none">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-tighter">{marketStatus.text}</span>
                <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">{marketStatus.countdown}</span>
            </div>
        </div>
    );
}
