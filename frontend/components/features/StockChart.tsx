/**
 * 股票 K 线图组件 (Stock Chart Component)
 * 职责：基于 lightweight-charts 渲染交互式 K 线、成交量、RSI、MACD 及布林带
 * 特色：支持多个子图表（Main, RSI, MACD）的十字线同步与时间周期的水平联动同步
 */
"use client";

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';

interface StockChartProps {
    data: any[];
    ticker: string;
    showBb?: boolean;
    showRsi?: boolean;
    showMacd?: boolean;
}

export const StockChart: React.FC<StockChartProps> = ({ data, ticker, showBb = true, showRsi = false, showMacd = false }) => {
    // 容器引用 (Container Refs)
    const mainContainerRef = useRef<HTMLDivElement>(null);
    const rsiContainerRef = useRef<HTMLDivElement>(null);
    const macdContainerRef = useRef<HTMLDivElement>(null);
    
    // 图表实例引用 (Chart API Refs)
    const mainChartRef = useRef<IChartApi | null>(null);
    const rsiChartRef = useRef<IChartApi | null>(null);
    const macdChartRef = useRef<IChartApi | null>(null);

    // 数据序列引用 (Series Refs)
    const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdSignalSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const macdHistSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

    // 布林带序列引用 (Bollinger Bands Series Refs)
    const bbUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const bbMiddleSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const bbLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

    // 防止内存泄漏：卸载哨兵 (Unmount Sentinel)
    const isUnmounted = useRef(false);
    
    // 副作用 1：初始化图表实例与联动逻辑 (Initialize Charts & Sync)
    useEffect(() => {
        isUnmounted.current = false;
        if (!mainContainerRef.current) return;

        // 图表通用视觉配置
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
                visible: false, // 默认隐藏，仅在最底部的图表上开启
            },
            crosshair: {
                mode: 0, // Magnet mode
            },
            handleScale: {
                axisPressedMouseMove: true,
            },
            rightPriceScale: {
                borderColor: 'rgba(148, 163, 184, 0.05)',
                visible: true,
            },
            watermark: {
                visible: false,
            }
        };

        // --- 1. 初始化主图表 (Initialize Main Chart) ---
        const mainChart = createChart(mainContainerRef.current, {
            ...commonOptions,
            height: 400,
            timeScale: {
                ...commonOptions.timeScale,
                visible: !showRsi && !showMacd, // 若无副图，主图显示时间轴
            },
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
            priceScaleId: '', // 叠在主图下方，不占用右侧主轴
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 }, // 布局在图表底部 20% 区域
        });

        // 布林带序列初始化 (If enabled)
        let bbUpper: ISeriesApi<"Line"> | null = null;
        let bbMiddle: ISeriesApi<"Line"> | null = null;
        let bbLower: ISeriesApi<"Line"> | null = null;

        if (showBb) {
            bbUpper = mainChart.addSeries(LineSeries, {
                color: 'rgba(244, 63, 94, 0.6)', 
                lineWidth: 1,
                lineStyle: 2, // 虚线
                crosshairMarkerVisible: false,
            });
            bbMiddle = mainChart.addSeries(LineSeries, {
                color: 'rgba(59, 130, 246, 0.4)',
                lineWidth: 1,
                crosshairMarkerVisible: false,
            });
            bbLower = mainChart.addSeries(LineSeries, {
                color: 'rgba(16, 185, 129, 0.6)',
                lineWidth: 1,
                lineStyle: 2,
                crosshairMarkerVisible: false,
            });
        }

        const syncItems: { chart: IChartApi; series: any }[] = [
            { chart: mainChart, series: candlestickSeries },
        ];

        // --- 2. 初始化 RSI 图表 (Initialize RSI Chart) ---
        let rsiChart: IChartApi | null = null;
        let rsiSeries: ISeriesApi<"Line"> | null = null;
        if (showRsi && rsiContainerRef.current) {
            rsiChart = createChart(rsiContainerRef.current, {
                ...commonOptions,
                height: 120,
                timeScale: {
                    ...commonOptions.timeScale,
                    visible: !showMacd, // 若无 MACD，RSI 显示时间轴
                },
            });
            rsiSeries = rsiChart.addSeries(LineSeries, {
                color: '#8b5cf6',
                lineWidth: 2,
            });
            // 70/30 超买超卖线
            rsiSeries.createPriceLine({
                price: 70, color: 'rgba(244, 63, 94, 0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true,
            });
            rsiSeries.createPriceLine({
                price: 30, color: 'rgba(16, 185, 129, 0.3)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true,
            });
            syncItems.push({ chart: rsiChart, series: rsiSeries });
        }

        // --- 3. 初始化 MACD 图表 (Initialize MACD Chart) ---
        let macdChart: IChartApi | null = null;
        let macdSeries: ISeriesApi<"Line"> | null = null;
        let macdSignalSeries: ISeriesApi<"Line"> | null = null;
        let macdHistSeries: ISeriesApi<"Histogram"> | null = null;
        if (showMacd && macdContainerRef.current) {
            macdChart = createChart(macdContainerRef.current, {
                ...commonOptions,
                height: 150,
                timeScale: {
                    ...commonOptions.timeScale,
                    visible: true, // 永远是底部，显示时间轴
                },
            });
            macdSeries = macdChart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1 });
            macdSignalSeries = macdChart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1 });
            macdHistSeries = macdChart.addSeries(HistogramSeries, { color: '#64748b' });
            syncItems.push({ chart: macdChart, series: macdSeries });
        }

        // --- 核心联动逻辑 (Core Synchronization Logic) ---
        let isSyncing = false;
        syncItems.forEach((item, index) => {
            // A. 时间缩放与平移联动 (Scale & Scroll Sync)
            item.chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
                if (!range || isUnmounted.current || isSyncing) return;
                
                isSyncing = true;
                syncItems.forEach((otherItem, otherIndex) => {
                    if (index !== otherIndex && otherItem.chart) {
                        try {
                            otherItem.chart.timeScale().setVisibleLogicalRange(range);
                        } catch (e) {}
                    }
                });
                isSyncing = false;
            });

            // B. 十字线指向联动 (Crosshair Move Sync)
            item.chart.subscribeCrosshairMove((param) => {
                if (isUnmounted.current) return;
                syncItems.forEach((otherItem, otherIndex) => {
                    if (index !== otherIndex && otherItem.chart && otherItem.series) {
                        try {
                            otherItem.chart.setCrosshairPosition(0, param.time as any, otherItem.series);
                        } catch (e) {}
                    }
                });
            });
        });

        // 存储引用
        mainChartRef.current = mainChart;
        rsiChartRef.current = rsiChart;
        macdChartRef.current = macdChart;
        
        candlestickSeriesRef.current = candlestickSeries;
        volumeSeriesRef.current = volumeSeries;
        rsiSeriesRef.current = rsiSeries;
        macdSeriesRef.current = macdSeries;
        macdSignalSeriesRef.current = macdSignalSeries;
        macdHistSeriesRef.current = macdHistSeries;
        
        bbUpperSeriesRef.current = bbUpper;
        bbMiddleSeriesRef.current = bbMiddle;
        bbLowerSeriesRef.current = bbLower;

        // 响应式调整 (Resize Handling)
        const handleResize = () => {
            if (isUnmounted.current) return;
            const width = mainContainerRef.current?.clientWidth || 0;
            try {
                mainChart.applyOptions({ width });
                rsiChart?.applyOptions({ width });
                macdChart?.applyOptions({ width });
            } catch (e) {}
        };

        window.addEventListener('resize', handleResize);
        
        // 清理 (Cleanup)
        return () => {
            isUnmounted.current = true;
            window.removeEventListener('resize', handleResize);
            try {
                mainChart.remove();
                rsiChart?.remove();
                macdChart?.remove();
            } catch (e) {}
        };
    }, [showBb, showRsi, showMacd]); // 显式依赖切换组件时的重绘

    // 副作用 2：数据流驱动更新 (Data Stream Updates)
    useEffect(() => {
        if (
            !isUnmounted.current &&
            candlestickSeriesRef.current && volumeSeriesRef.current && 
            data && data.length > 0
        ) {
            try {
                // 主图数据解析
                const chartData = data.map(item => ({
                    time: item.time,
                    open: item.open, high: item.high, low: item.low, close: item.close,
                }));

                const volumeData = data.map(item => ({
                    time: item.time,
                    value: item.volume,
                    color: item.close >= item.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)',
                }));

                candlestickSeriesRef.current.setData(chartData);
                volumeSeriesRef.current.setData(volumeData);
                
                // 布林带数据更新
                if (showBb && bbUpperSeriesRef.current && bbMiddleSeriesRef.current && bbLowerSeriesRef.current) {
                    const bbUpperData = data.map(item => ({ time: item.time, value: item.bb_upper ?? undefined }));
                    const bbMiddleData = data.map(item => ({ time: item.time, value: item.bb_middle ?? undefined }));
                    const bbLowerData = data.map(item => ({ time: item.time, value: item.bb_lower ?? undefined }));
                    
                    bbUpperSeriesRef.current.setData(bbUpperData as any);
                    bbMiddleSeriesRef.current.setData(bbMiddleData as any);
                    bbLowerSeriesRef.current.setData(bbLowerData as any);
                }
                
                // RSI 数据更新
                if (showRsi && rsiSeriesRef.current) {
                    const rsiData = data.map(item => ({ 
                        time: item.time, 
                        value: item.rsi !== null ? item.rsi : undefined 
                    }));
                    rsiSeriesRef.current.setData(rsiData as any);
                }
                
                // MACD 数据更新
                if (showMacd && macdSeriesRef.current && macdSignalSeriesRef.current && macdHistSeriesRef.current) {
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
                    
                    macdSeriesRef.current.setData(macdData as any);
                    macdSignalSeriesRef.current.setData(macdSignalData as any);
                    macdHistSeriesRef.current.setData(macdHistData as any);
                }
                
                // 默认填充整个屏幕视图 (Fit view)
                mainChartRef.current?.timeScale().fitContent();
            } catch (e) {
                console.error("Failed to update chart data", e);
            }
        }
    }, [data, showBb, showRsi, showMacd]);

    return (
        <div className="w-full relative bg-white dark:bg-slate-900 rounded-[2.5rem] border border-slate-100 dark:border-slate-800 p-2 overflow-hidden shadow-sm flex flex-col gap-1">
            {/* 叠层水印标题 (Layered Watermark Header) */}
            <div className="absolute top-6 left-8 z-10 flex flex-col pointer-events-none">
                <span className="text-[10px] font-black uppercase text-slate-400 tracking-[0.3em] opacity-60">Market Perspective</span>
                <span className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">{ticker}</span>
            </div>
            
            {/* 主图容器 */}
            <div ref={mainContainerRef} className="w-full" />
            
            {/* RSI 副图容器 */}
            {showRsi && (
                <>
                    <div className="mt-2 px-6 flex items-center justify-between">
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">RSI (14)</span>
                    </div>
                    <div ref={rsiContainerRef} className="w-full" />
                </>
            )}
            
            {/* MACD 副图容器 */}
            {showMacd && (
                <>
                    <div className="mt-2 px-6 flex items-center justify-between">
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">MACD (12, 26, 9)</span>
                    </div>
                    <div ref={macdContainerRef} className="w-full" />
                </>
            )}
        </div>
    );
};
