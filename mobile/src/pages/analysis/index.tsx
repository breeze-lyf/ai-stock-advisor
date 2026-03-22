import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useState, useEffect, useCallback } from 'react'
import { analysisApi, AnalysisResponse } from '@/services/analysis'
import './index.scss'

export default function AnalysisPage() {
  const router = useRouter()
  const ticker = router.params.ticker || ''
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadAnalysis = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await analysisApi.analyzeStock(ticker)
      setAnalysis(result)
    } catch (error) {
      Taro.showToast({ title: '获取分析失败', icon: 'none' })
    } finally {
      setIsLoading(false)
    }
  }, [ticker])

  useEffect(() => {
    if (ticker) {
      void loadAnalysis()
    }
  }, [loadAnalysis, ticker])

  const refreshAnalysis = useCallback(async () => {
    Taro.showLoading({ title: 'AI 分析中...' })
    try {
      const result = await analysisApi.analyzeStock(ticker, true)
      setAnalysis(result)
      Taro.showToast({ title: '分析完成', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '分析失败', icon: 'none' })
    } finally {
      Taro.hideLoading()
    }
  }, [ticker])

  return (
    <View className="analysis-page">
      <View className="header">
        <Text className="title">{ticker} 分析报告</Text>
        <View className="refresh-btn" onClick={refreshAnalysis}>
          <Text>刷新</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>AI 分析中...</Text>
          </View>
        ) : analysis ? (
          <View className="analysis-content">
            <View className="section">
              <Text className="section-title">核心观点</Text>
              <View className="card">
                <Text>{analysis.core_logic_summary || '暂无分析'}</Text>
              </View>
            </View>

            <View className="section">
              <Text className="section-title">操作建议</Text>
              <View className="card">
                <Text className="highlight">{analysis.action_advice || '--'}</Text>
              </View>
            </View>

            {analysis.technical_analysis && (
              <View className="section">
                <Text className="section-title">技术分析</Text>
                <View className="card">
                  <Text>{analysis.technical_analysis}</Text>
                </View>
              </View>
            )}

            {analysis.fundamental_analysis && (
              <View className="section">
                <Text className="section-title">基本面分析</Text>
                <View className="card">
                  <Text>{analysis.fundamental_analysis}</Text>
                </View>
              </View>
            )}
          </View>
        ) : (
          <View className="empty">
            <Text>暂无分析数据</Text>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
