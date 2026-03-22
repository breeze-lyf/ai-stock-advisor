import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import EChart from './EChart'

interface PieChartData {
  name: string
  value: number
  color?: string
}

interface PieChartProps {
  data: PieChartData[]
  title?: string
  height?: number
  showLegend?: boolean
  donut?: boolean  // 环形图
  roseType?: boolean | 'radius' | 'area'  // 南丁格尔图
}

const PieChartComponent: React.FC<PieChartProps> = ({
  data,
  title,
  height = 280,
  showLegend = true,
  donut = true,
  roseType = false
}) => {
  const option = useMemo<EChartsOption>(() => {
    if (!data || data.length === 0) {
      return {}
    }

    // 默认颜色方案
    const defaultColors = [
      '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', 
      '#a855f7', '#06b6d4', '#ec4899', '#14b8a6'
    ]

    const pieData = data.map((item, index) => ({
      name: item.name,
      value: item.value,
      itemStyle: {
        color: item.color || defaultColors[index % defaultColors.length]
      }
    }))

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
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        textStyle: {
          color: '#1f2937',
          fontSize: 12
        },
        formatter: (params: any) => {
          return `<div style="font-size:12px">
            <div style="font-weight:500">${params.name}</div>
            <div>
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${params.color};margin-right:4px"></span>
              ${params.value} (${params.percent}%)
            </div>
          </div>`
        }
      },
      legend: showLegend ? {
        orient: 'horizontal',
        bottom: 10,
        textStyle: {
          fontSize: 10,
          color: '#6b7280'
        },
        itemWidth: 10,
        itemHeight: 10
      } : undefined,
      series: [{
        type: 'pie',
        radius: donut ? ['40%', '70%'] : '70%',
        center: ['50%', showLegend ? '45%' : '50%'],
        roseType: roseType === true ? 'radius' : roseType || undefined,
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: donut ? 6 : 0,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          fontSize: 10,
          color: '#6b7280',
          formatter: '{b}: {d}%'
        },
        labelLine: {
          show: true,
          length: 10,
          length2: 10,
          lineStyle: {
            color: '#d1d5db'
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          },
          label: {
            show: true,
            fontWeight: 'bold'
          }
        },
        data: pieData
      }]
    }
  }, [data, title, showLegend, donut, roseType])

  return <EChart option={option} height={height} />
}

export default PieChartComponent
