import type { EChartsOption } from 'echarts'
import { useMemo } from 'react'
import EChart from './EChart'
import './CandlestickChart.scss'

interface KLineData {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume?: number
}

interface CandlestickChartProps {
  data: KLineData[]
  title?: string
  height?: number
  showVolume?: boolean
  showMA?: boolean
  maLines?: number[]  // MA 周期，如 [5, 10, 20]
}

// 计算移动平均线
const calculateMA = (data: KLineData[], dayCount: number): (number | null)[] => {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < dayCount - 1) {
      result.push(null)
      continue
    }
    let sum = 0
    for (let j = 0; j < dayCount; j++) {
      sum += data[i - j].close
    }
    result.push(+(sum / dayCount).toFixed(2))
  }
  return result
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  title,
  height = 400,
  showVolume = true,
  showMA = true,
  maLines = [5, 10, 20]
}) => {
  const option = useMemo<EChartsOption>(() => {
    if (!data || data.length === 0) {
      return {}
    }

    const dates = data.map(item => item.date)
    const klineData = data.map(item => [item.open, item.close, item.low, item.high])
    const volumeData = data.map((item, _index) => ({
      value: item.volume || 0,
      itemStyle: {
        color: item.close >= item.open ? '#ef4444' : '#22c55e'
      }
    }))

    const series: any[] = [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData,
        itemStyle: {
          color: '#ef4444',        // 阳线填充色
          color0: '#22c55e',       // 阴线填充色
          borderColor: '#ef4444',  // 阳线边框色
          borderColor0: '#22c55e'  // 阴线边框色
        }
      }
    ]

    // 添加均线
    if (showMA) {
      const colors = ['#f59e0b', '#3b82f6', '#a855f7']
      maLines.forEach((days, index) => {
        series.push({
          name: `MA${days}`,
          type: 'line',
          data: calculateMA(data, days),
          smooth: true,
          lineStyle: {
            width: 1,
            color: colors[index % colors.length]
          },
          symbol: 'none'
        })
      })
    }

    const gridConfig: any[] = [
      {
        left: '10%',
        right: '8%',
        top: title ? 60 : 30,
        height: showVolume ? '50%' : '70%'
      }
    ]

    const xAxisConfig: any[] = [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { color: '#6b7280', fontSize: 10 },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ]

    const yAxisConfig: any[] = [
      {
        scale: true,
        splitArea: { show: true },
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { color: '#6b7280', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f3f4f6' } }
      }
    ]

    // 添加成交量图
    if (showVolume) {
      gridConfig.push({
        left: '10%',
        right: '8%',
        top: '75%',
        height: '15%'
      })

      xAxisConfig.push({
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisLabel: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      })

      yAxisConfig.push({
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      })

      series.push({
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData
      })
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
          type: 'cross'
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        textStyle: {
          color: '#1f2937',
          fontSize: 12
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          const date = params[0].axisValue
          let result = `<div style="font-weight:500;margin-bottom:4px">${date}</div>`
          
          params.forEach((item: any) => {
            if (item.seriesType === 'candlestick') {
              const [open, close, low, high] = item.data
              result += `
                <div style="color:#6b7280;font-size:11px">
                  开: ${open} 高: ${high}<br/>
                  低: ${low} 收: ${close}
                </div>
              `
            } else if (item.seriesType === 'line' && item.value != null) {
              result += `<div style="color:${item.color};font-size:11px">${item.seriesName}: ${item.value}</div>`
            }
          })
          return result
        }
      },
      legend: {
        data: showMA ? maLines.map(d => `MA${d}`) : [],
        top: title ? 30 : 5,
        textStyle: { fontSize: 10, color: '#6b7280' }
      },
      grid: gridConfig,
      xAxis: xAxisConfig,
      yAxis: yAxisConfig,
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 60,
          end: 100
        },
        {
          show: true,
          xAxisIndex: showVolume ? [0, 1] : [0],
          type: 'slider',
          bottom: 5,
          height: 20,
          start: 60,
          end: 100
        }
      ],
      series
    }
  }, [data, title, showVolume, showMA, maLines])

  return <EChart option={option} height={height} />
}

export default CandlestickChart
