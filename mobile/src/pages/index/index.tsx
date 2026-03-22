import { View, Text, ScrollView, Input } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useEffect, useCallback, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { usePortfolioStore } from '@/store/portfolioStore'
import './index.scss'

export default function IndexPage() {
  const { isAuthenticated, user } = useAuthStore()
  const { summary, fetchSummary, isLoading } = usePortfolioStore()
  const [searchValue, setSearchValue] = useState('')

  useDidShow(() => {
    // 每次页面显示时检查登录状态
    if (!isAuthenticated) {
      Taro.redirectTo({ url: '/pages/login/index' })
      return
    }
    fetchSummary()
  })

  useEffect(() => {
    if (isAuthenticated) {
      fetchSummary()
    }
  }, [isAuthenticated, fetchSummary])

  const navigateTo = useCallback((url: string) => {
    Taro.navigateTo({ url })
  }, [])

  const handleSearch = useCallback(() => {
    if (searchValue.trim()) {
      Taro.navigateTo({ url: '/pages/portfolio/add' })
    }
  }, [searchValue])

  const formatCurrency = (value: number) => {
    return value.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })
  }

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(2)}%`
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <ScrollView className="index-page" scrollY>
      {/* 顶部问候 + 警报入口 */}
      <View className="header">
        <View className="greeting">
          <Text className="greeting-text">你好，{user?.email?.split('@')[0] || '投资者'}</Text>
          <Text className="greeting-subtitle">今日市场</Text>
        </View>
        <View className="header-actions">
          <View className="alert-btn" onClick={() => navigateTo('/pages/alerts/index')}>
            <Text className="alert-icon">🔔</Text>
          </View>
        </View>
      </View>

      {/* 搜索框 */}
      <View className="search-bar">
        <Input
          className="search-input"
          placeholder="搜索股票代码或名称"
          value={searchValue}
          onInput={(e) => setSearchValue(e.detail.value)}
          onConfirm={handleSearch}
        />
        <View className="search-btn" onClick={handleSearch}>
          <Text>搜索</Text>
        </View>
      </View>

      {/* 组合概览卡片 */}
      <View className="summary-card">
        <Text className="card-title">投资组合总览</Text>
        {isLoading && !summary ? (
          <View className="loading">
            <View className="loading-spinner" />
          </View>
        ) : summary ? (
          <>
            <View className="total-value">
              <Text className="value-label">总市值</Text>
              <Text className="value-amount">{formatCurrency(summary.total_market_value)}</Text>
            </View>
            <View className="stats-row">
              <View className="stat-item">
                <Text className="stat-label">今日盈亏</Text>
                <Text className={`stat-value ${summary.day_change >= 0 ? 'price-up' : 'price-down'}`}>
                  {formatCurrency(summary.day_change)}
                </Text>
              </View>
              <View className="stat-item">
                <Text className="stat-label">总收益率</Text>
                <Text className={`stat-value ${summary.total_pl_percent >= 0 ? 'price-up' : 'price-down'}`}>
                  {formatPercent(summary.total_pl_percent)}
                </Text>
              </View>
            </View>
            <View className="holdings-count">
              <Text>持仓 {summary.holdings?.length || 0} 只</Text>
            </View>
          </>
        ) : (
          <View className="empty-state">
            <Text className="empty-text">暂无持仓数据</Text>
            <View className="empty-action" onClick={() => Taro.switchTab({ url: '/pages/portfolio/index' })}>
              <Text>去添加股票</Text>
            </View>
          </View>
        )}
      </View>

      {/* 快捷功能 */}
      <View className="quick-actions">
        <Text className="section-title">快捷功能</Text>
        <View className="action-grid">
          <View className="action-item" onClick={() => navigateTo('/pages/analysis/portfolio')}>
            <View className="action-icon analysis-icon">AI</View>
            <Text className="action-label">组合分析</Text>
          </View>
          <View className="action-item" onClick={() => Taro.switchTab({ url: '/pages/macro/index' })}>
            <View className="action-icon macro-icon">宏</View>
            <Text className="action-label">宏观雷达</Text>
          </View>
          <View className="action-item" onClick={() => navigateTo('/pages/paper-trading/index')}>
            <View className="action-icon trade-icon">模</View>
            <Text className="action-label">模拟交易</Text>
          </View>
          <View className="action-item" onClick={() => Taro.switchTab({ url: '/pages/settings/index' })}>
            <View className="action-icon settings-icon">设</View>
            <Text className="action-label">设置</Text>
          </View>
        </View>
      </View>

      {/* 热门持仓 */}
      {summary?.holdings && summary.holdings.length > 0 && (
        <View className="hot-holdings">
          <Text className="section-title">持仓速览</Text>
          <View className="holdings-list">
            {summary.holdings.slice(0, 5).map((item) => (
              <View
                key={item.ticker}
                className="holding-item"
                onClick={() => navigateTo(`/pages/stock/detail?ticker=${item.ticker}`)}
              >
                <View className="holding-info">
                  <Text className="holding-ticker">{item.ticker}</Text>
                  <Text className="holding-name">{item.name}</Text>
                </View>
                <View className="holding-price">
                  <Text className="price">{item.price?.toFixed(2) || '--'}</Text>
                  <Text className={`change ${(item.weight || 0) >= 0 ? 'price-up' : 'price-down'}`}>
                    {item.weight ? `${item.weight.toFixed(1)}%` : '--'}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}
    </ScrollView>
  )
}
