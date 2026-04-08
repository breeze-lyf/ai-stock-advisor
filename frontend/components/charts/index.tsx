"use client";

import { useMemo } from "react";

interface LineChartProps {
  data: Array<{ x: string; y: number; series?: string }>;
  xAxisLabel?: string;
  yAxisLabel?: string;
  width?: number;
  height?: number;
}

export function LineChart({ data, xAxisLabel = "", yAxisLabel = "", width = 600, height = 250 }: LineChartProps) {
  const { path, xTicks, yTicks, minY, maxY } = useMemo(() => {
    if (!data || data.length === 0) return { path: "", xTicks: [], yTicks: [], minY: 0, maxY: 0 };

    const values = data.map(d => d.y);
    const minY = Math.min(...values);
    const maxY = Math.max(...values);
    const padding = (maxY - minY) * 0.1 || 1;
    const actualMinY = minY - padding;
    const actualMaxY = maxY + padding;

    const chartWidth = width - 60;
    const chartHeight = height - 40;

    const xScale = (index: number) => (index / (data.length - 1)) * chartWidth;
    const yScale = (value: number) => chartHeight - ((value - actualMinY) / (actualMaxY - actualMinY)) * chartHeight;

    const path = data
      .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(i) + 50} ${yScale(d.y) + 30}`)
      .join(" ");

    // X 轴刻度（显示 5 个）
    const xTickCount = Math.min(5, data.length);
    const xStep = Math.floor(data.length / xTickCount);
    const xTicks = Array.from({ length: xTickCount }, (_, i) => ({
      value: data[i * xStep]?.x || "",
      x: xScale(i * xStep) + 50,
    })).filter((t, i, arr) => i === 0 || i === arr.length - 1 || !arr.slice(0, i).some(prev => prev.value === t.value));

    // Y 轴刻度（显示 5 个）
    const yTickCount = 5;
    const yStep = (actualMaxY - actualMinY) / (yTickCount - 1);
    const yTicks = Array.from({ length: yTickCount }, (_, i) => ({
      value: actualMinY + yStep * i,
      y: yScale(actualMinY + yStep * i) + 30,
    }));

    return { path, xTicks, yTicks, minY: actualMinY, maxY: actualMaxY };
  }, [data, width, height]);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-full text-slate-400">No data</div>;
  }

  return (
    <svg width={width} height={height} className="overflow-hidden">
      {/* Y 轴标签 */}
      {yAxisLabel && (
        <text x={10} y={height / 2} transform={`rotate(-90, 10, ${height / 2})`} className="text-xs fill-slate-500">
          {yAxisLabel}
        </text>
      )}

      {/* Y 轴刻度 */}
      {yTicks.map((tick, i) => (
        <g key={`y-${i}`}>
          <line x1={50} y1={tick.y} x2={width - 10} y2={tick.y} stroke="#e2e8f0" strokeDasharray="4" />
          <text x={45} y={tick.y + 4} textAnchor="end" className="text-xs fill-slate-500">
            {(tick.value * 100).toFixed(0)}%
          </text>
        </g>
      ))}

      {/* X 轴刻度 */}
      {xTicks.map((tick, i) => (
        <g key={`x-${i}`}>
          <text x={tick.x} y={height - 10} textAnchor="middle" className="text-xs fill-slate-500">
            {tick.value.slice(5)}
          </text>
        </g>
      ))}

      {/* 折线 */}
      <path d={path} fill="none" stroke="#3b82f6" strokeWidth={2} />

      {/* X 轴标签 */}
      {xAxisLabel && (
        <text x={width / 2} y={height - 2} textAnchor="middle" className="text-xs fill-slate-500">
          {xAxisLabel}
        </text>
      )}

      {/* 边框 */}
      <rect x={50} y={30} width={width - 60} height={height - 40} fill="none" stroke="#e2e8f0" />
    </svg>
  );
}

interface BarChartProps {
  data: Array<{ x: string; y: number }>;
  xAxisLabel?: string;
  yAxisLabel?: string;
  width?: number;
  height?: number;
}

export function BarChart({ data, xAxisLabel = "", yAxisLabel = "", width = 600, height = 250 }: BarChartProps) {
  const { bars, yTicks } = useMemo(() => {
    if (!data || data.length === 0) return { bars: [], yTicks: [] };

    const values = data.map(d => d.y);
    const minY = Math.min(0, Math.min(...values));
    const maxY = Math.max(...values);
    const padding = (maxY - minY) * 0.1 || 1;
    const actualMinY = minY - padding;
    const actualMaxY = maxY + padding;

    const chartWidth = width - 60;
    const chartHeight = height - 40;
    const barWidth = chartWidth / data.length - 4;

    const xScale = (index: number) => index * (chartWidth / data.length) + 50;
    const yScale = (value: number) => chartHeight - ((value - actualMinY) / (actualMaxY - actualMinY)) * chartHeight + 30;

    const bars = data.map((d, i) => {
      const barWidth = chartWidth / data.length - 4;
      return {
        x: xScale(i) + 2,
        y: yScale(Math.max(0, d.y)),
        width: barWidth,
        height: Math.abs(yScale(d.y) - yScale(0)),
        value: d.y,
        color: d.y >= 0 ? "#22c55e" : "#ef4444",
      };
    });

    const yTickCount = 5;
    const yStep = (actualMaxY - actualMinY) / (yTickCount - 1);
    const yTicks = Array.from({ length: yTickCount }, (_, i) => ({
      value: actualMinY + yStep * i,
      y: yScale(actualMinY + yStep * i),
    }));

    return { bars, yTicks };
  }, [data, width, height]);

  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-full text-slate-400">No data</div>;
  }

  return (
    <svg width={width} height={height} className="overflow-hidden">
      {/* Y 轴刻度 */}
      {yTicks.map((tick, i) => (
        <g key={`y-${i}`}>
          <line x1={50} y1={tick.y} x2={width - 10} y2={tick.y} stroke="#e2e8f0" strokeDasharray="4" />
          <text x={45} y={tick.y + 4} textAnchor="end" className="text-xs fill-slate-500">
            {(tick.value * 100).toFixed(0)}%
          </text>
        </g>
      ))}

      {/* 柱状图 */}
      {bars.map((bar, i) => (
        <rect
          key={i}
          x={bar.x}
          y={bar.y}
          width={bar.width}
          height={Math.max(1, bar.height)}
          fill={bar.color}
          rx={2}
        />
      ))}

      {/* X 轴刻度 */}
      {data.slice(0, 10).map((d, i) => (
        <text
          key={`x-${i}`}
          x={50 + i * ((width - 60) / Math.min(10, data.length)) + (width - 60) / Math.min(10, data.length) / 2}
          y={height - 10}
          textAnchor="middle"
          className="text-xs fill-slate-500"
        >
          {d.x.slice(5)}
        </text>
      ))}

      {/* 边框 */}
      <rect x={50} y={30} width={width - 60} height={height - 40} fill="none" stroke="#e2e8f0" />
    </svg>
  );
}
