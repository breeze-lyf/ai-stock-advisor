import { useRef, useEffect, forwardRef, useImperativeHandle, useCallback } from 'react'
import { View, Canvas } from '@tarojs/components'
import Taro from '@tarojs/taro'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, CandlestickChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import './EChart.scss'

// 定义 ECharts 实例类型
type EChartsInstance = ReturnType<typeof echarts.init>

// 注册 ECharts 组件
echarts.use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  CandlestickChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
])

interface EChartProps {
  option: EChartsOption
  width?: string | number
  height?: string | number
  onInit?: (chart: EChartsInstance) => void
  onChartReady?: (chart: EChartsInstance) => void
}

export interface EChartRef {
  getInstance: () => EChartsInstance | null
  setOption: (option: EChartsOption) => void
  resize: () => void
  dispose: () => void
}

const EChart = forwardRef<EChartRef, EChartProps>((props, ref) => {
  const { option, width = '100%', height = 300, onInit, onChartReady } = props
  const chartRef = useRef<EChartsInstance | null>(null)
  const canvasId = useRef(`ec-canvas-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`)

  const initWeappChart = useCallback(() => {
    const query = Taro.createSelectorQuery()
    query
      .select(`#${canvasId.current}`)
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res || !res[0]) return

        const canvasNode = res[0].node
        const canvasWidth = res[0].width
        const canvasHeight = res[0].height

        const dpr = Taro.getWindowInfo().pixelRatio || 1
        canvasNode.width = canvasWidth * dpr
        canvasNode.height = canvasHeight * dpr

        chartRef.current = echarts.init(canvasNode, null, {
          width: canvasWidth,
          height: canvasHeight,
          devicePixelRatio: dpr,
          renderer: 'canvas'
        })

        chartRef.current.setOption(option)
        onInit?.(chartRef.current)
        onChartReady?.(chartRef.current)
      })
  }, [onChartReady, onInit, option])

  useImperativeHandle(ref, () => ({
    getInstance: () => chartRef.current,
    setOption: (opt: EChartsOption) => {
      if (chartRef.current) {
        chartRef.current.setOption(opt)
      }
    },
    resize: () => {
      if (chartRef.current) {
        chartRef.current.resize()
      }
    },
    dispose: () => {
      if (chartRef.current) {
        chartRef.current.dispose()
        chartRef.current = null
      }
    }
  }))

  useEffect(() => {
    const initChart = async () => {
      const env = Taro.getEnv()

      if (env === Taro.ENV_TYPE.WEB) {
        // H5 环境：直接使用 DOM
        const container = document.getElementById(canvasId.current)
        if (container) {
          chartRef.current = echarts.init(container)
          chartRef.current.setOption(option)
          onInit?.(chartRef.current)
          onChartReady?.(chartRef.current)
        }
      } else if (env === Taro.ENV_TYPE.WEAPP) {
        // 微信小程序环境
        initWeappChart()
      }
    }

    // 延迟初始化确保 DOM 已渲染
    setTimeout(initChart, 100)

    return () => {
      if (chartRef.current) {
        chartRef.current.dispose()
        chartRef.current = null
      }
    }
  }, [initWeappChart, onChartReady, onInit, option])

  // 当 option 变化时更新图表
  useEffect(() => {
    if (chartRef.current && option) {
      chartRef.current.setOption(option, true)
    }
  }, [option])

  const env = Taro.getEnv()
  const styleObj = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height
  }

  if (env === Taro.ENV_TYPE.WEB) {
    return (
      <View className="echart-container" style={styleObj}>
        <View id={canvasId.current} style={{ width: '100%', height: '100%' }} />
      </View>
    )
  }

  // 小程序环境使用 Canvas 2D
  return (
    <View className="echart-container" style={styleObj}>
      <Canvas
        type="2d"
        id={canvasId.current}
        canvasId={canvasId.current}
        style={{ width: '100%', height: '100%' }}
      />
    </View>
  )
})

EChart.displayName = 'EChart'

export default EChart
