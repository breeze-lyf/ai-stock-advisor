"use client";

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';

interface StockChartProps {
    data: any[];
    ticker: string;
}

export const StockChart: React.FC<StockChartProps> = ({ data, ticker }) => {
    const mainContainerRef = useRef<HTMLDivElement>(null);
    const rsiContainerRef = useRef<HTMLDivElement>(null);
    const macdContainerRef = useRef<HTMLDivElement>(null);
    
    const mainChartRef = useRef<IChartApi | null>(null);
    const rsiChartRef = useRef<IChartApi | null>(null);
    const macdChartRef = useRef<IChartApi | null>(null);

    const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdSignalSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdHistSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

    const isUnmounted = useRef(false);
    
    useEffect(() => {
        isUnmounted.current = false;
        if (!mainContainerRef.current || !rsiContainerRef.current || !macdContainerRef.current) return;

        const commonOptions = {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(148, 163, 184, 0.05)' },
                horzLines: { color: 'rgba(148, 163, 184, 0.05)' },
            },
            width: mainContainerRef.current.clientWidth,
            timeScale: {
                borderColor: 'rgba(148, 163, 184, 0.2)',
                visible: false, // Hidden for upper charts
            },
            crosshair: {
                mode: 0,
            },
            handleScale: {
                axisPressedMouseMove: true,
            },
            priceScale: {
                minimumWidth: 80,
            },
        };

        // 1. Create Main Chart
        const mainChart = createChart(mainContainerRef.current, {
            ...commonOptions,
            height: 350,
        });
        const candlestickSeries = mainChart.addSeries(CandlestickSeries, {
            upColor: '#10b981',
            downColor: '#f43f5e',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#f43f5e',
        });
        const volumeSeries = mainChart.addSeries(HistogramSeries, {
            color: '#3b82f6',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });

        // 2. Create RSI Chart
        const rsiChart = createChart(rsiContainerRef.current, {
            ...commonOptions,
            height: 120,
        });
        const rsiSeries = rsiChart.addSeries(LineSeries, {
            color: '#8b5cf6',
            lineWidth: 2,
        });
        rsiSeries.createPriceLine({
            price: 70, color: 'rgba(244, 63, 94, 0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true,
        });
        rsiSeries.createPriceLine({
            price: 30, color: 'rgba(16, 185, 129, 0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true,
        });

        // 3. Create MACD Chart
        const macdChart = createChart(macdContainerRef.current, {
            ...commonOptions,
            height: 150,
            timeScale: {
                ...commonOptions.timeScale,
                visible: true, // Show time scale on last chart
            },
        });
        const macdSeries = macdChart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1 });
        const macdSignalSeries = macdChart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1 });
        const macdHistSeries = macdChart.addSeries(HistogramSeries, { color: '#64748b' });

        // --- Synchronization Logic ---
        const syncItems = [
            { chart: mainChart, series: candlestickSeries },
            { chart: rsiChart, series: rsiSeries },
            { chart: macdChart, series: macdSeries },
        ];
        
        let isSyncing = false;
        syncItems.forEach((item, index) => {
            item.chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
                if (!range || isUnmounted.current || isSyncing) return;
                
                isSyncing = true;
                syncItems.forEach((otherItem, otherIndex) => {
                    if (index !== otherIndex && otherItem.chart) {
                        try {
                            otherItem.chart.timeScale().setVisibleLogicalRange(range);
                        } catch (e) {
                            // Ignore potential errors during unmount
                        }
                    }
                });
                isSyncing = false;
            });

            item.chart.subscribeCrosshairMove((param) => {
                if (isUnmounted.current) return;
                syncItems.forEach((otherItem, otherIndex) => {
                    if (index !== otherIndex && otherItem.chart && otherItem.series) {
                        try {
                            // param.time will be undefined if the mouse is outside, which clears coordinate
                            otherItem.chart.setCrosshairPosition(0, param.time as any, otherItem.series);
                        } catch (e) {
                            // Ignore potential errors during unmount
                        }
                    }
                });
            });
        });

        mainChartRef.current = mainChart;
        rsiChartRef.current = rsiChart;
        macdChartRef.current = macdChart;
        
        candlestickSeriesRef.current = candlestickSeries;
        volumeSeriesRef.current = volumeSeries;
        rsiSeriesRef.current = rsiSeries;
        macdSeriesRef.current = macdSeries;
        macdSignalSeriesRef.current = macdSignalSeries;
        macdHistSeriesRef.current = macdHistSeries;

        const handleResize = () => {
            if (isUnmounted.current) return;
            const width = mainContainerRef.current?.clientWidth || 0;
            try {
                mainChart.applyOptions({ width });
                rsiChart.applyOptions({ width });
                macdChart.applyOptions({ width });
            } catch (e) {}
        };

        window.addEventListener('resize', handleResize);
        return () => {
            isUnmounted.current = true;
            window.removeEventListener('resize', handleResize);
            try {
                mainChart.remove();
                rsiChart.remove();
                macdChart.remove();
            } catch (e) {}
        };
    }, []);

    useEffect(() => {
        if (
            !isUnmounted.current &&
            candlestickSeriesRef.current && volumeSeriesRef.current && 
            rsiSeriesRef.current && macdSeriesRef.current && 
            macdSignalSeriesRef.current && macdHistSeriesRef.current &&
            data && data.length > 0
        ) {
            try {
                const chartData = data.map(item => ({
                    time: item.time,
                    open: item.open, high: item.high, low: item.low, close: item.close,
                }));

                const volumeData = data.map(item => ({
                    time: item.time,
                    value: item.volume,
                    color: item.close >= item.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)',
                }));

                const rsiData = data.map(item => ({ 
                    time: item.time, 
                    value: item.rsi !== null ? item.rsi : undefined 
                }));
                const macdData = data.map(item => ({ 
                    time: item.time, 
                    value: item.macd !== null ? item.macd : undefined 
                }));
                const macdSignalData = data.map(item => ({ 
                    time: item.time, 
                    value: item.macd_signal !== null ? item.macd_signal : undefined 
                }));
                const macdHistData = data.map(item => ({
                    time: item.time,
                    value: item.macd_hist !== null ? item.macd_hist : undefined,
                    color: (item.macd_hist ?? 0) >= 0 ? 'rgba(16, 185, 129, 0.5)' : 'rgba(244, 63, 94, 0.5)',
                }));

                candlestickSeriesRef.current.setData(chartData);
                volumeSeriesRef.current.setData(volumeData);
                rsiSeriesRef.current.setData(rsiData as any);
                macdSeriesRef.current.setData(macdData as any);
                macdSignalSeriesRef.current.setData(macdSignalData as any);
                macdHistSeriesRef.current.setData(macdHistData as any);
                
                mainChartRef.current?.timeScale().fitContent();
            } catch (e) {
                console.error("Failed to update chart data", e);
            }
        }
    }, [data]);

    return (
        <div className="w-full relative bg-white dark:bg-slate-900 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 p-2 overflow-hidden shadow-sm flex flex-col gap-1">
            <div className="absolute top-6 left-8 z-10 flex flex-col pointer-events-none">
                <span className="text-[10px] font-black uppercase text-slate-400 tracking-[0.3em] opacity-60">Market Perspective</span>
                <span className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">{ticker}</span>
            </div>
            
            <div ref={mainContainerRef} className="w-full" />
            
            <div className="px-6 flex items-center justify-between">
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">RSI (14)</span>
            </div>
            <div ref={rsiContainerRef} className="w-full" />
            
            <div className="px-6 flex items-center justify-between">
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">MACD (12, 26, 9)</span>
            </div>
            <div ref={macdContainerRef} className="w-full" />
        </div>
    );
};
