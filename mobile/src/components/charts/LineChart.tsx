import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import EChart from './EChart'

interface LineChartData {
  date: string
  value: number
}

interface LineChartProps {
  data: LineChartData[]
  title?: string
  height?: number
  color?: string
  areaStyle?: boolean
  smooth?: boolean
  showSymbol?: boolean
  yAxisFormatter?: (value: number) => string
}

const LineChartComponent: React.FC<LineChartProps> = ({
  data,
  title,
  height = 250,
  color = '#3b82f6',
  areaStyle = true,
  smooth = true,
  showSymbol = false,
  yAxisFormatter
}) => {
  const option = useMemo<EChartsOption>(() => {
    if (!data || data.length === 0) {
      return {}
    }

    const dates = data.map(item => item.date)
    const values = data.map(item => item.value)

    // 计算涨跌颜色
    const isPositive = values.length > 0 && values[values.length - 1] >= values[0]
    const lineColor = isPositive ? '#22c55e' : '#ef4444'

    return {
      title: title ? {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 14,
          fontWeight: 500,
          color: '#1f2937'
        }
      } : undefined,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        textStyle: {
          color: '#1f2937',
          fontSize: 12
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          const item = params[0]
          const value = yAxisFormatter ? yAxisFormatter(item.value) : item.value
          return `<div style="font-size:12px">
            <div style="font-weight:500">${item.axisValue}</div>
            <div style="color:${item.color}">${value}</div>
          </div>`
        }
      },
      grid: {
        left: '12%',
        right: '5%',
        top: title ? 50 : 20,
        bottom: 30
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: {
          color: '#6b7280',
          fontSize: 10,
          formatter: (value: string) => {
            // 简化日期显示
            const parts = value.split('-')
            return parts.length >= 2 ? `${parts[1]}/${parts[2] || ''}` : value
          }
        },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: {
          color: '#6b7280',
          fontSize: 10,
          formatter: yAxisFormatter
        },
        splitLine: {
          lineStyle: { color: '#f3f4f6' }
        }
      },
      series: [{
        type: 'line',
        data: values,
        smooth,
        symbol: showSymbol ? 'circle' : 'none',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: color === 'auto' ? lineColor : color
        },
        itemStyle: {
          color: color === 'auto' ? lineColor : color
        },
        areaStyle: areaStyle ? {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: (color === 'auto' ? lineColor : color) + '40' },
              { offset: 1, color: (color === 'auto' ? lineColor : color) + '05' }
            ]
          }
        } : undefined
      }]
    }
  }, [data, title, color, areaStyle, smooth, showSymbol, yAxisFormatter])

  return <EChart option={option} height={height} />
}

export default LineChartComponent
