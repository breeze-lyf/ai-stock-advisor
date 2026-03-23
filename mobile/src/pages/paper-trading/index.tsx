import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useCallback, useState } from 'react'
import { paperTradingApi } from '@/services'
import type { SimulatedTrade } from '@/types/domain'
import './index.scss'

export default function PaperTradingPage() {
  const [trades, setTrades] = useState<SimulatedTrade[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadTrades = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await paperTradingApi.getTrades()
      setTrades(data)
    } catch (error) {
      console.error('获取模拟交易失败:', error)
      Taro.showToast({ title: '加载交易失败', icon: 'none' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  useDidShow(() => {
    void loadTrades()
  })

  const openCreatePage = useCallback(() => {
    Taro.navigateTo({ url: '/pages/paper-trading/create' })
  }, [])

  const activeTrades = trades.filter((trade) => trade.status === 'OPEN')
  const closedTrades = trades.filter((trade) => trade.status !== 'OPEN')

  const formatPercent = (value?: number | null) => {
    if (typeof value !== 'number') return '--'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatPrice = (value?: number | null) => {
    if (typeof value !== 'number') return '--'
    return value.toFixed(2)
  }

  const getStatusLabel = (status: SimulatedTrade['status']) => {
    switch (status) {
      case 'CLOSED_PROFIT':
        return '获利平仓'
      case 'CLOSED_LOSS':
        return '止损平仓'
      case 'CLOSED_MANUAL':
        return '手动平仓'
      default:
        return '进行中'
    }
  }

  return (
    <View className="paper-trading-page">
      <View className="header">
        <View>
          <Text className="title">模拟交易</Text>
          <Text className="subtitle">验证交易计划与目标位</Text>
        </View>
        <View className="primary-btn" onClick={openCreatePage}>
          <Text>新建交易</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>加载中...</Text>
          </View>
        ) : (
          <>
            <View className="stats-grid">
              <View className="stat-card">
                <Text className="stat-label">进行中</Text>
                <Text className="stat-value">{activeTrades.length}</Text>
              </View>
              <View className="stat-card">
                <Text className="stat-label">已关闭</Text>
                <Text className="stat-value">{closedTrades.length}</Text>
              </View>
            </View>

            {trades.length === 0 ? (
              <View className="empty-state">
                <Text className="empty-icon">📈</Text>
                <Text className="empty-title">暂无模拟交易</Text>
                <Text className="empty-desc">创建一笔交易来跟踪目标价和止损位。</Text>
                <View className="primary-btn full" onClick={openCreatePage}>
                  <Text>创建第一笔</Text>
                </View>
              </View>
            ) : (
              <View className="trade-list">
                {trades.map((trade) => {
                  const pnl = trade.unrealized_pnl_pct ?? trade.realized_pnl_pct ?? null
                  return (
                    <View key={trade.id} className="trade-card">
                      <View className="trade-head">
                        <View>
                          <Text className="trade-ticker">{trade.ticker}</Text>
                          <Text className="trade-date">
                            {new Date(trade.entry_date).toLocaleDateString('zh-CN')}
                          </Text>
                        </View>
                        <View className={`status-badge ${trade.status === 'OPEN' ? 'open' : 'closed'}`}>
                          <Text>{getStatusLabel(trade.status)}</Text>
                        </View>
                      </View>

                      <View className="trade-grid">
                        <View className="trade-metric">
                          <Text className="metric-label">入场价</Text>
                          <Text className="metric-value">{formatPrice(trade.entry_price)}</Text>
                        </View>
                        <View className="trade-metric">
                          <Text className="metric-label">现价</Text>
                          <Text className="metric-value">{formatPrice(trade.current_price)}</Text>
                        </View>
                        <View className="trade-metric">
                          <Text className="metric-label">目标价</Text>
                          <Text className="metric-value">{formatPrice(trade.target_price)}</Text>
                        </View>
                        <View className="trade-metric">
                          <Text className="metric-label">止损价</Text>
                          <Text className="metric-value">{formatPrice(trade.stop_loss_price)}</Text>
                        </View>
                      </View>

                      <View className="trade-footer">
                        <Text className={`pnl ${typeof pnl === 'number' && pnl >= 0 ? 'up' : 'down'}`}>
                          {formatPercent(pnl)}
                        </Text>
                        <Text className="reason">{trade.entry_reason || '未填写入场理由'}</Text>
                      </View>
                    </View>
                  )
                })}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </View>
  )
}
