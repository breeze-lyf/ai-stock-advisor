import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useCallback } from 'react'
import { usePortfolioStore } from '@/store/portfolioStore'
import type { PortfolioItem } from '@/types/domain'
import './index.scss'

export default function PortfolioPage() {
  const { items, isLoading, fetchPortfolio, removeItem, refreshAll } = usePortfolioStore()

  useDidShow(() => {
    fetchPortfolio()
  })

  const handleRefresh = useCallback(async () => {
    Taro.showLoading({ title: '刷新中...' })
    await refreshAll()
    Taro.hideLoading()
    Taro.showToast({ title: '刷新完成', icon: 'success' })
  }, [refreshAll])

  const handleDelete = useCallback(async (item: PortfolioItem) => {
    const res = await Taro.showModal({
      title: '确认删除',
      content: `确定要删除 ${item.ticker} 吗？`,
      confirmColor: '#ef4444',
    })
    if (res.confirm) {
      const success = await removeItem(item.ticker)
      if (success) {
        Taro.showToast({ title: '已删除', icon: 'success' })
      }
    }
  }, [removeItem])

  const goToDetail = useCallback((ticker: string) => {
    Taro.navigateTo({ url: `/pages/stock/detail?ticker=${ticker}` })
  }, [])

  const goToAdd = useCallback(() => {
    Taro.navigateTo({ url: '/pages/portfolio/add' })
  }, [])

  return (
    <View className="portfolio-page">
      {/* 顶部操作栏 */}
      <View className="header">
        <Text className="title">我的持仓</Text>
        <View className="actions">
          <View className="action-btn" onClick={handleRefresh}>
            <Text>刷新</Text>
          </View>
          <View className="action-btn primary" onClick={goToAdd}>
            <Text>添加</Text>
          </View>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading && items.length === 0 ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text className="loading-text">加载中...</Text>
          </View>
        ) : items.length === 0 ? (
          <View className="empty">
            <Text className="empty-icon">📊</Text>
            <Text className="empty-text">暂无持仓</Text>
            <Text className="empty-hint">点击右上角添加股票</Text>
          </View>
        ) : (
          <View className="stock-list">
            {items.map((item) => (
              <View
                key={item.ticker}
                className="stock-card"
                onClick={() => goToDetail(item.ticker)}
                onLongPress={() => handleDelete(item)}
              >
                <View className="stock-info">
                  <View className="stock-header">
                    <Text className="ticker">{item.ticker}</Text>
                    <Text className="name">{item.name}</Text>
                  </View>
                  <View className="stock-meta">
                    <Text className="meta-item">持仓: {item.quantity} 股</Text>
                    <Text className="meta-item">成本: ¥{item.cost_basis.toFixed(2)}</Text>
                  </View>
                </View>
                <View className="stock-price">
                  <Text className="current-price">
                    {item.price ? `¥${item.price.toFixed(2)}` : '--'}
                  </Text>
                  {item.weight !== undefined && item.weight !== null && (
                    <Text className={`price-change ${item.weight >= 0 ? 'up' : 'down'}`}>
                      {item.weight >= 0 ? '+' : ''}{item.weight.toFixed(2)}%
                    </Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      <View className="footer-hint">
        <Text>长按卡片可删除持仓</Text>
      </View>
    </View>
  )
}
