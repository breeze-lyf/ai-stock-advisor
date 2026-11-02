"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";

interface MarketStatusIndicatorProps {
    className?: string;
}

export function MarketStatusIndicator({ className }: MarketStatusIndicatorProps) {
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
            const status: 'open' | 'closed' = isOpen ? 'open' : 'closed';

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
        <div className={clsx("flex h-8 items-center gap-2 rounded-lg border border-line px-2.5 text-[11.5px]", className)}>
            <span className={clsx("h-1.5 w-1.5 rounded-full", marketStatus.status === 'open' ? "bg-emerald-500 shadow-[0_0_0_3px_rgb(16_185_129/0.15)]" : "bg-ink-3")} />
            <span className="text-ink-3">{marketStatus.text}</span>
            <span className="num font-medium text-ink-2">{marketStatus.countdown}</span>
        </div>
    );
}
