import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect, useCallback } from 'react'
import { analysisApi, PortfolioAnalysisResponse } from '@/services/analysis'
import './portfolio.scss'

export default function PortfolioAnalysisPage() {
  const [analysis, setAnalysis] = useState<PortfolioAnalysisResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadAnalysis()
  }, [])

  const loadAnalysis = async () => {
    setIsLoading(true)
    try {
      const result = await analysisApi.getLatestPortfolioAnalysis()
      setAnalysis(result)
    } catch (error) {
      console.error('获取分析失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const requestAnalysis = useCallback(async () => {
    Taro.showLoading({ title: 'AI 分析中...' })
    try {
      const result = await analysisApi.analyzePortfolio(true)
      setAnalysis(result)
      Taro.showToast({ title: '分析完成', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: '分析失败', icon: 'none' })
    } finally {
      Taro.hideLoading()
    }
  }, [])

  const getHealthColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f59e0b'
    return '#ef4444'
  }

  return (
    <View className="portfolio-analysis-page">
      <View className="header">
        <Text className="title">投资组合分析</Text>
        <View className="action-btn" onClick={requestAnalysis}>
          <Text>AI 分析</Text>
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
            <View className="health-card">
              <View className="health-score" style={{ borderColor: getHealthColor(analysis.health_score) }}>
                <Text className="score" style={{ color: getHealthColor(analysis.health_score) }}>
                  {analysis.health_score}
                </Text>
                <Text className="label">健康评分</Text>
              </View>
              <View className="health-info">
                <View className="info-item">
                  <Text className="info-label">风险等级</Text>
                  <Text className="info-value">{analysis.risk_level}</Text>
                </View>
              </View>
            </View>

            <View className="section">
              <Text className="section-title">投资概要</Text>
              <View className="card">
                <Text>{analysis.summary}</Text>
              </View>
            </View>

            <View className="section">
              <Text className="section-title">分散化分析</Text>
              <View className="card">
                <Text>{analysis.diversification_analysis}</Text>
              </View>
            </View>

            <View className="section">
              <Text className="section-title">战略建议</Text>
              <View className="card">
                <Text>{analysis.strategic_advice}</Text>
              </View>
            </View>

            {analysis.top_risks?.length > 0 && (
              <View className="section">
                <Text className="section-title">主要风险</Text>
                <View className="list-card">
                  {analysis.top_risks.map((risk, index) => (
                    <View key={index} className="list-item risk">
                      <Text className="bullet">!</Text>
                      <Text>{risk}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {analysis.top_opportunities?.length > 0 && (
              <View className="section">
                <Text className="section-title">主要机会</Text>
                <View className="list-card">
                  {analysis.top_opportunities.map((opp, index) => (
                    <View key={index} className="list-item opportunity">
                      <Text className="bullet">✓</Text>
                      <Text>{opp}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </>
        ) : (
          <View className="empty">
            <Text className="empty-icon">📊</Text>
            <Text className="empty-text">暂无分析数据</Text>
            <View className="empty-action" onClick={requestAnalysis}>
              <Text>开始 AI 分析</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  )
}
