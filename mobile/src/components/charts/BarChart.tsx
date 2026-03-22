import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import EChart from './EChart'

interface BarChartData {
  name: string
  value: number
  color?: string
}

interface BarChartProps {
  data: BarChartData[]
  title?: string
  height?: number
  horizontal?: boolean
  showLabel?: boolean
  colorByValue?: boolean  // 根据值正负着色
}

const BarChartComponent: React.FC<BarChartProps> = ({
  data,
  title,
  height = 250,
  horizontal = false,
  showLabel = true,
  colorByValue = false
}) => {
  const option = useMemo<EChartsOption>(() => {
    if (!data || data.length === 0) {
      return {}
    }

    const names = data.map(item => item.name)
    const values = data.map((item, index) => {
      const defaultColors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7']
      let color = item.color || defaultColors[index % defaultColors.length]
      
      // 根据正负值着色
      if (colorByValue) {
        color = item.value >= 0 ? '#22c55e' : '#ef4444'
      }
      
      return {
        value: item.value,
        itemStyle: { color }
      }
    })

    const categoryAxis: any = {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: {
        color: '#6b7280',
        fontSize: 10,
        interval: 0,
        rotate: horizontal ? 0 : (names.length > 5 ? 30 : 0)
      },
      axisTick: { show: false }
    }

    const valueAxis: any = {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#6b7280',
        fontSize: 10
      },
      splitLine: {
        lineStyle: { color: '#f3f4f6' }
      }
    }

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
        axisPointer: {
          type: 'shadow'
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        textStyle: {
          color: '#1f2937',
          fontSize: 12
        }
      },
      grid: {
        left: horizontal ? '20%' : '10%',
        right: '5%',
        top: title ? 50 : 20,
        bottom: horizontal ? 30 : 50
      },
      xAxis: horizontal ? valueAxis : categoryAxis,
      yAxis: horizontal ? categoryAxis : valueAxis,
      series: [{
        type: 'bar',
        data: values,
        barWidth: '60%',
        label: showLabel ? {
          show: true,
          position: horizontal ? 'right' : 'top',
          fontSize: 10,
          color: '#6b7280',
          formatter: (params: any) => {
            const val = params.value
            return colorByValue ? (val >= 0 ? '+' : '') + val.toFixed(2) + '%' : val
          }
        } : undefined,
        itemStyle: {
          borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]
        }
      }]
    }
  }, [data, title, horizontal, showLabel, colorByValue])

  return <EChart option={option} height={height} />
}

export default BarChartComponent
