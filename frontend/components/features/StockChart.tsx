"use client";

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

interface StockChartProps {
    data: any[];
    ticker: string;
}

export const StockChart: React.FC<StockChartProps> = ({ data, ticker }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Create Chart
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8', // slate-400
            },
            grid: {
                vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
                horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            timeScale: {
                borderColor: 'rgba(148, 163, 184, 0.2)',
            },
        });

        chart.timeScale().fitContent();

        // Add Candlestick Series - v5 API
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#10b981', // emerald-500
            downColor: '#f43f5e', // rose-500
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#f43f5e',
        });

        // Add Volume Series - v5 API
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#3b82f6', // blue-500
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '', // set as an overlay
        });

        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8, // volume takes 20% of the height at the bottom
                bottom: 0,
            },
        });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;
        volumeSeriesRef.current = volumeSeries;

        const handleResize = () => {
            if (chartContainerRef.current && chartRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (candlestickSeriesRef.current && volumeSeriesRef.current && data && data.length > 0) {
            // Mapping data for Candlestick
            const chartData = data.map(item => ({
                time: item.time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));

            // Mapping data for Volume
            const volumeData = data.map(item => ({
                time: item.time,
                value: item.volume,
                color: item.close >= item.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)',
            }));

            candlestickSeriesRef.current.setData(chartData);
            volumeSeriesRef.current.setData(volumeData);
            chartRef.current?.timeScale().fitContent();
        }
    }, [data]);

    return (
        <div className="w-full relative bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 p-2 overflow-hidden shadow-sm mt-4">
            <div className="absolute top-4 left-6 z-10 flex flex-col pointer-events-none">
                <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest opacity-60">Historical Price Action</span>
                <span className="text-xl font-black text-slate-900 dark:text-white uppercase">{ticker}</span>
            </div>
            <div ref={chartContainerRef} className="w-full" />
        </div>
    );
};
