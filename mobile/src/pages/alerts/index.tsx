import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { alertsApi, NotificationLog } from '@/services/alerts'
import './index.scss'

export default function AlertsPage() {
  const [logs, setLogs] = useState<NotificationLog[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useDidShow(() => {
    loadAlerts()
  })

  const loadAlerts = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await alertsApi.getNotificationHistory(30)
      setLogs(data)
    } catch (error) {
      console.error('获取通知失败:', error)
      Taro.showToast({ title: '获取通知失败', icon: 'none' })
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getTypeInfo = (type: string) => {
    switch (type) {
      case 'MACRO_ALERT':
        return { label: '宏观雷达', color: '#f59e0b', icon: '⚡' }
      case 'PRICE_ALERT':
        return { label: '价格监控', color: '#22c55e', icon: '📈' }
      case 'DAILY_REPORT':
        return { label: '每日体检', color: '#3b82f6', icon: '📅' }
      case 'INDICATOR_ALERT':
        return { label: '指标告警', color: '#ef4444', icon: '⚠️' }
      default:
        return { label: '系统通知', color: '#71717a', icon: '🔔' }
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  return (
    <View className="alerts-page">
      <View className="header">
        <View className="header-content">
          <Text className="header-icon">⚡</Text>
          <View className="header-text">
            <Text className="header-title">智能提醒流</Text>
            <Text className="header-subtitle">Smart Alert Stream</Text>
          </View>
        </View>
        <View className="sync-badge">
          <Text>实时同步</Text>
        </View>
      </View>

      <ScrollView className="content" scrollY>
        {isLoading ? (
          <View className="loading">
            <View className="loading-spinner" />
            <Text>加载中...</Text>
          </View>
        ) : logs.length === 0 ? (
          <View className="empty">
            <Text className="empty-icon">🔔</Text>
            <Text className="empty-text">暂无推送历史</Text>
            <Text className="empty-hint">系统探针正在持续工作中...</Text>
          </View>
        ) : (
          <View className="timeline">
            {logs.map((log) => {
              const typeInfo = getTypeInfo(log.type)
              return (
                <View key={log.id} className="timeline-item">
                  {/* 时间线圆点 */}
                  <View className="timeline-dot" style={{ backgroundColor: typeInfo.color }} />
                  
                  {/* 卡片内容 */}
                  <View className="alert-card">
                    <View className="card-header">
                      <View className="type-badge" style={{ backgroundColor: `${typeInfo.color}20`, borderColor: `${typeInfo.color}40` }}>
                        <Text className="type-icon">{typeInfo.icon}</Text>
                        <Text className="type-label" style={{ color: typeInfo.color }}>{typeInfo.label}</Text>
                      </View>
                      <Text className="time">{formatTime(log.created_at)}</Text>
                    </View>
                    
                    <Text className="card-title">{log.title}</Text>
                    
                    {log.content && (
                      <Text className="card-content">{log.content}</Text>
                    )}
                    
                    <View className="card-footer">
                      <Text className="channel">渠道: 飞书机器人</Text>
                    </View>
                  </View>
                </View>
              )
            })}
          </View>
        )}
      </ScrollView>
    </View>
  )
}
