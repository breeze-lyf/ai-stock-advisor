import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useState, useEffect, useCallback } from 'react'
import { analysisApi, AnalysisResponse } from '@/services/analysis'
import './detail.scss'

export default function StockDetailPage() {
  const router = useRouter()
  const ticker = router.params.ticker || ''
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const loadLatestAnalysis = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await analysisApi.getLatestAnalysis(ticker)
      setAnalysis(result)
    } catch (error) {
      console.error('获取分析失败:', error)
    } finally {
      setIsLoading(false)
    }
  }, [ticker])

  useEffect(() => {
    if (ticker) {
      void loadLatestAnalysis()
    }
  }, [loadLatestAnalysis, ticker])

  const requestAnalysis = useCallback(async (forceRefresh = false) => {
    setIsAnalyzing(true)
    Taro.showLoading({ title: 'AI 分析中...' })
    try {
      const result = await analysisApi.analyzeStock(ticker, forceRefresh)
      setAnalysis(result)
      Taro.showToast({ title: '分析完成', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '分析失败', icon: 'none' })
    } finally {
      setIsAnalyzing(false)
      Taro.hideLoading()
    }
  }, [ticker])

  const getRiskColor = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'low': return '#22c55e'
      case 'medium': return '#f59e0b'
      case 'high': return '#ef4444'
      default: return '#71717a'
    }
  }

  return (
    <View className="detail-page">
      {/* 股票头部信息 */}
      <View className="header">
        <View className="stock-info">
          <Text className="ticker">{ticker}</Text>
          <Text className="status">{analysis?.summary_status || '待分析'}</Text>
        </View>
        <View className="action-btn" onClick={() => requestAnalysis(true)}>
          <Text>{isAnalyzing ? '分析中...' : 'AI 分析'}</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>加载中...</Text>
          </View>
        ) : analysis ? (
          <>
            {/* 核心摘要 */}
            <View className="section">
              <Text className="section-title">核心观点</Text>
              <View className="summary-card">
                <Text className="summary-text">{analysis.core_logic_summary || '暂无分析'}</Text>
              </View>
            </View>

            {/* 操作建议 */}
            <View className="section">
              <Text className="section-title">操作建议</Text>
              <View className="advice-card">
                <View className="advice-item">
                  <Text className="advice-label">建议操作</Text>
                  <Text className="advice-value highlight">{analysis.action_advice || '--'}</Text>
                </View>
                <View className="advice-item">
                  <Text className="advice-label">风险等级</Text>
                  <Text className="advice-value" style={{ color: getRiskColor(analysis.risk_level) }}>
                    {analysis.risk_level || '--'}
                  </Text>
                </View>
                <View className="advice-item">
                  <Text className="advice-label">置信度</Text>
                  <Text className="advice-value">{analysis.confidence_level ? `${analysis.confidence_level}%` : '--'}</Text>
                </View>
              </View>
            </View>

            {/* 价格目标 */}
            <View className="section">
              <Text className="section-title">价格目标</Text>
              <View className="price-grid">
                <View className="price-item">
                  <Text className="price-label">目标价 1</Text>
                  <Text className="price-value up">{analysis.target_price_1 ? `¥${analysis.target_price_1}` : '--'}</Text>
                </View>
                <View className="price-item">
                  <Text className="price-label">目标价 2</Text>
                  <Text className="price-value up">{analysis.target_price_2 ? `¥${analysis.target_price_2}` : '--'}</Text>
                </View>
                <View className="price-item">
                  <Text className="price-label">止损价</Text>
                  <Text className="price-value down">{analysis.stop_loss_price ? `¥${analysis.stop_loss_price}` : '--'}</Text>
                </View>
                <View className="price-item">
                  <Text className="price-label">风险收益比</Text>
                  <Text className="price-value">{analysis.rr_ratio || '--'}</Text>
                </View>
              </View>
            </View>

            {/* 触发条件 */}
            {(analysis.trigger_condition || analysis.invalidation_condition) && (
              <View className="section">
                <Text className="section-title">触发条件</Text>
                <View className="condition-card">
                  {analysis.trigger_condition && (
                    <View className="condition-item">
                      <Text className="condition-label">入场条件</Text>
                      <Text className="condition-text">{analysis.trigger_condition}</Text>
                    </View>
                  )}
                  {analysis.invalidation_condition && (
                    <View className="condition-item">
                      <Text className="condition-label">失效条件</Text>
                      <Text className="condition-text">{analysis.invalidation_condition}</Text>
                    </View>
                  )}
                </View>
              </View>
            )}

            {/* 分析详情 */}
            {analysis.technical_analysis && (
              <View className="section">
                <Text className="section-title">技术分析</Text>
                <View className="detail-card">
                  <Text className="detail-text">{analysis.technical_analysis}</Text>
                </View>
              </View>
            )}

            {analysis.fundamental_analysis && (
              <View className="section">
                <Text className="section-title">基本面分析</Text>
                <View className="detail-card">
                  <Text className="detail-text">{analysis.fundamental_analysis}</Text>
                </View>
              </View>
            )}

            {/* 缓存信息 */}
            <View className="footer-info">
              <Text>
                {analysis.is_cached ? '缓存数据 | ' : ''}
                模型: {analysis.model_used || 'Unknown'}
                {analysis.created_at && ` | ${new Date(analysis.created_at).toLocaleDateString()}`}
              </Text>
            </View>
          </>
        ) : (
          <View className="empty">
            <Text className="empty-icon">🔍</Text>
            <Text className="empty-text">暂无分析数据</Text>
            <View className="empty-action" onClick={() => requestAnalysis()}>
              <Text>开始 AI 分析</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
