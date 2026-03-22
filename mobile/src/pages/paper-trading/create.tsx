import { View, Text, Input, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useCallback, useRef, useState } from 'react'
import { paperTradingApi, portfolioApi } from '@/services'
import './create.scss'

interface SearchResult {
  ticker: string
  name: string
}

export default function CreateTradePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [selectedStock, setSelectedStock] = useState<SearchResult | null>(null)
  const [entryPrice, setEntryPrice] = useState('')
  const [targetPrice, setTargetPrice] = useState('')
  const [stopLossPrice, setStopLossPrice] = useState('')
  const [entryReason, setEntryReason] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const searchTimer = useRef<NodeJS.Timeout>()

  const handleSearch = useCallback((value: string) => {
    setSearchQuery(value)

    if (searchTimer.current) {
      clearTimeout(searchTimer.current)
    }

    if (!value.trim()) {
      setSearchResults([])
      return
    }

    searchTimer.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const results = await portfolioApi.searchStocks(value)
        setSearchResults(results)
      } catch (error) {
        console.error('搜索股票失败:', error)
      } finally {
        setIsSearching(false)
      }
    }, 300)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!selectedStock) {
      Taro.showToast({ title: '请选择股票', icon: 'none' })
      return
    }
    if (!entryPrice || Number(entryPrice) <= 0) {
      Taro.showToast({ title: '请输入有效入场价', icon: 'none' })
      return
    }
    if (!entryReason.trim()) {
      Taro.showToast({ title: '请填写入场理由', icon: 'none' })
      return
    }

    setIsSaving(true)
    try {
      await paperTradingApi.createTrade({
        ticker: selectedStock.ticker,
        entry_price: Number(entryPrice),
        entry_reason: entryReason.trim(),
        target_price: targetPrice ? Number(targetPrice) : undefined,
        stop_loss_price: stopLossPrice ? Number(stopLossPrice) : undefined,
      })
      Taro.showToast({ title: '创建成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1000)
    } catch (error) {
      console.error('创建模拟交易失败:', error)
      Taro.showToast({ title: '创建失败', icon: 'none' })
    } finally {
      setIsSaving(false)
    }
  }, [entryPrice, entryReason, selectedStock, stopLossPrice, targetPrice])

  return (
    <View className="create-trade-page">
      <ScrollView className="content" scrollY>
        <View className="section">
          <Text className="section-title">选择股票</Text>
          <Input
            className="input"
            placeholder="输入股票代码或名称"
            value={searchQuery}
            onInput={(e) => handleSearch(e.detail.value)}
          />
          {isSearching && (
            <Text className="hint">搜索中...</Text>
          )}
          {searchResults.length > 0 && (
            <View className="result-list">
              {searchResults.map((item) => (
                <View
                  key={item.ticker}
                  className="result-item"
                  onClick={() => {
                    setSelectedStock(item)
                    setSearchQuery(item.ticker)
                    setSearchResults([])
                  }}
                >
                  <Text className="result-ticker">{item.ticker}</Text>
                  <Text className="result-name">{item.name}</Text>
                </View>
              ))}
            </View>
          )}
          {selectedStock && (
            <View className="selected-stock">
              <Text>{selectedStock.ticker} · {selectedStock.name}</Text>
            </View>
          )}
        </View>

        <View className="section">
          <Text className="section-title">交易计划</Text>
          <Input
            className="input"
            type="digit"
            placeholder="入场价"
            value={entryPrice}
            onInput={(e) => setEntryPrice(e.detail.value)}
          />
          <Input
            className="input"
            type="digit"
            placeholder="目标价（可选）"
            value={targetPrice}
            onInput={(e) => setTargetPrice(e.detail.value)}
          />
          <Input
            className="input"
            type="digit"
            placeholder="止损价（可选）"
            value={stopLossPrice}
            onInput={(e) => setStopLossPrice(e.detail.value)}
          />
          <Input
            className="input textarea"
            type="text"
            placeholder="入场理由"
            value={entryReason}
            onInput={(e) => setEntryReason(e.detail.value)}
          />
        </View>

        <View className={`submit-btn ${isSaving ? 'disabled' : ''}`} onClick={handleSubmit}>
          <Text>{isSaving ? '提交中...' : '创建模拟交易'}</Text>
        </View>
      </ScrollView>
    </View>
  )
}
