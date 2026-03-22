import { View, Text, Input, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback, useRef } from 'react'
import { portfolioApi } from '@/services/portfolio'
import { usePortfolioStore } from '@/store/portfolioStore'
import './add.scss'

interface SearchResult {
  ticker: string
  name: string
  exchange?: string
}

export default function AddPortfolioPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedStock, setSelectedStock] = useState<SearchResult | null>(null)
  const [quantity, setQuantity] = useState('')
  const [costBasis, setCostBasis] = useState('')
  const searchTimer = useRef<NodeJS.Timeout>()
  
  const { addItem, isLoading } = usePortfolioStore()

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
        console.error('搜索失败:', error)
      } finally {
        setIsSearching(false)
      }
    }, 300)
  }, [])

  const selectStock = useCallback((stock: SearchResult) => {
    setSelectedStock(stock)
    setSearchQuery('')
    setSearchResults([])
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!selectedStock) {
      Taro.showToast({ title: '请选择股票', icon: 'none' })
      return
    }
    if (!quantity || parseFloat(quantity) <= 0) {
      Taro.showToast({ title: '请输入有效数量', icon: 'none' })
      return
    }
    if (!costBasis || parseFloat(costBasis) <= 0) {
      Taro.showToast({ title: '请输入有效成本', icon: 'none' })
      return
    }

    const success = await addItem(
      selectedStock.ticker,
      parseFloat(quantity),
      parseFloat(costBasis)
    )

    if (success) {
      Taro.showToast({ title: '添加成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    }
  }, [selectedStock, quantity, costBasis, addItem])

  return (
    <View className="add-page">
      {/* 搜索框 */}
      <View className="search-section">
        <Text className="section-title">搜索股票</Text>
        <Input
          className="search-input"
          placeholder="输入股票代码或名称"
          placeholderClass="input-placeholder"
          value={searchQuery}
          onInput={(e) => handleSearch(e.detail.value)}
        />
        
        {/* 搜索结果 */}
        {searchResults.length > 0 && (
          <ScrollView className="search-results" scrollY>
            {searchResults.map((item) => (
              <View
                key={item.ticker}
                className="result-item"
                onClick={() => selectStock(item)}
              >
                <Text className="result-ticker">{item.ticker}</Text>
                <Text className="result-name">{item.name}</Text>
                <Text className="result-exchange">{item.exchange || '--'}</Text>
              </View>
            ))}
          </ScrollView>
        )}
        
        {isSearching && (
          <View className="searching">
            <Text>搜索中...</Text>
          </View>
        )}
      </View>

      {/* 已选股票 */}
      {selectedStock && (
        <View className="selected-section">
          <Text className="section-title">已选股票</Text>
          <View className="selected-card">
            <View className="selected-info">
              <Text className="selected-ticker">{selectedStock.ticker}</Text>
              <Text className="selected-name">{selectedStock.name}</Text>
            </View>
            <View className="selected-remove" onClick={() => setSelectedStock(null)}>
              <Text>移除</Text>
            </View>
          </View>
        </View>
      )}

      {/* 数量和成本 */}
      {selectedStock && (
        <View className="form-section">
          <View className="form-item">
            <Text className="form-label">持仓数量（股）</Text>
            <Input
              className="form-input"
              type="digit"
              placeholder="请输入持仓数量"
              placeholderClass="input-placeholder"
              value={quantity}
              onInput={(e) => setQuantity(e.detail.value)}
            />
          </View>
          
          <View className="form-item">
            <Text className="form-label">成本价（元）</Text>
            <Input
              className="form-input"
              type="digit"
              placeholder="请输入平均成本价"
              placeholderClass="input-placeholder"
              value={costBasis}
              onInput={(e) => setCostBasis(e.detail.value)}
            />
          </View>
        </View>
      )}

      {/* 提交按钮 */}
      {selectedStock && (
        <View className="submit-section">
          <View
            className={`submit-btn ${isLoading ? 'disabled' : ''}`}
            onClick={handleSubmit}
          >
            <Text>{isLoading ? '添加中...' : '添加到持仓'}</Text>
          </View>
        </View>
      )}
    </View>
  )
}
