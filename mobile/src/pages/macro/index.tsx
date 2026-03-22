import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { macroApi, GlobalNews, MacroRadarResponse } from '@/services/macro'
import './index.scss'

export default function MacroPage() {
  const [radar, setRadar] = useState<MacroRadarResponse | null>(null)
  const [news, setNews] = useState<GlobalNews[]>([])
  const [activeTab, setActiveTab] = useState<'radar' | 'news'>('radar')
  const [isLoading, setIsLoading] = useState(false)

  useDidShow(() => {
    loadData()
  })

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [radarData, newsData] = await Promise.all([
        macroApi.getMacroRadar(),
        macroApi.getClsNews(20),
      ])
      setRadar(radarData)
      setNews(newsData)
    } catch (error) {
      console.error('加载数据失败:', error)
      Taro.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getHeatColor = (score: number) => {
    if (score >= 80) return '#ef4444'
    if (score >= 60) return '#f59e0b'
    return '#22c55e'
  }

  return (
    <View className="macro-page">
      {/* Tab 切换 */}
      <View className="tabs">
        <View
          className={`tab ${activeTab === 'radar' ? 'active' : ''}`}
          onClick={() => setActiveTab('radar')}
        >
          <Text>宏观雷达</Text>
        </View>
        <View
          className={`tab ${activeTab === 'news' ? 'active' : ''}`}
          onClick={() => setActiveTab('news')}
        >
          <Text>财经资讯</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>加载中...</Text>
          </View>
        ) : activeTab === 'radar' ? (
          /* 宏观雷达视图 */
          <View className="radar-view">
            {radar?.summary && (
              <View className="summary-card">
                <Text className="summary-title">市场概览</Text>
                <Text className="summary-text">{radar.summary}</Text>
              </View>
            )}

            {radar?.items && radar.items.length > 0 ? (
              <View className="radar-list">
                {radar.items.map((item, index) => (
                  <View key={index} className="radar-item">
                    <View className="radar-header">
                      <Text className="radar-category">{item.title}</Text>
                      <Text
                        className="radar-trend"
                        style={{ color: getHeatColor(item.heat_score) }}
                      >
                        热度 {Math.round(item.heat_score)}
                      </Text>
                    </View>
                    <View className="radar-body">
                      <Text className="radar-indicator">{item.impact_analysis?.logic || '暂无传导逻辑'}</Text>
                      <Text className="radar-value">{item.updated_at.slice(0, 16).replace('T', ' ')}</Text>
                    </View>
                    <View className="radar-footer">
                      <Text className="radar-description">{item.summary || '暂无摘要'}</Text>
                      <Text
                        className="radar-impact"
                        style={{ color: getHeatColor(item.heat_score) }}
                      >
                        利好 {item.impact_analysis?.beneficiaries?.length || 0} | 利空 {item.impact_analysis?.detriments?.length || 0}
                      </Text>
                    </View>
                  </View>
                ))}
              </View>
            ) : (
              <View className="empty">
                <Text>暂无宏观数据</Text>
              </View>
            )}
          </View>
        ) : (
          /* 财经资讯视图 */
          <View className="news-view">
            {news.length > 0 ? (
              <View className="news-list">
                {news.map((item, index) => (
                  <View key={index} className="news-item">
                    <Text className="news-time">{item.time}</Text>
                    <Text className="news-title">{item.title}</Text>
                    {item.content && (
                      <Text className="news-content">{item.content}</Text>
                    )}
                  </View>
                ))}
              </View>
            ) : (
              <View className="empty">
                <Text>暂无资讯</Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </View>
  )
}
