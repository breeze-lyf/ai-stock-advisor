import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import './index.scss'

export default function SettingsPage() {
  const { user, logout } = useAuthStore()

  const handleLogout = useCallback(() => {
    Taro.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmColor: '#ef4444',
      success: (res) => {
        if (res.confirm) {
          logout()
        }
      },
    })
  }, [logout])

  const navigateTo = useCallback((url: string) => {
    Taro.navigateTo({ url })
  }, [])

  return (
    <View className="settings-page">
      <ScrollView className="content" scrollY>
        {/* 用户信息 */}
        <View className="user-section">
          <View className="avatar">
            <Text>{user?.email?.charAt(0).toUpperCase() || 'U'}</Text>
          </View>
          <Text className="email">{user?.email || '未登录'}</Text>
        </View>

        {/* 功能列表 */}
        <View className="menu-section">
          <Text className="section-title">账号设置</Text>
          <View className="menu-list">
            <View className="menu-item" onClick={() => navigateTo('/pages/settings/password')}>
              <Text className="menu-label">修改密码</Text>
              <Text className="menu-arrow">›</Text>
            </View>
          </View>
        </View>

        <View className="menu-section">
          <Text className="section-title">快捷入口</Text>
          <View className="menu-list">
            <View className="menu-item" onClick={() => navigateTo('/pages/alerts/index')}>
              <Text className="menu-label">消息通知</Text>
              <Text className="menu-arrow">›</Text>
            </View>
            <View className="menu-item" onClick={() => navigateTo('/pages/analysis/portfolio')}>
              <Text className="menu-label">组合分析</Text>
              <Text className="menu-arrow">›</Text>
            </View>
            <View className="menu-item" onClick={() => navigateTo('/pages/paper-trading/index')}>
              <Text className="menu-label">模拟交易</Text>
              <Text className="menu-arrow">›</Text>
            </View>
          </View>
        </View>

        <View className="menu-section">
          <Text className="section-title">高级设置</Text>
          <View className="menu-list">
            <View className="menu-item" onClick={() => navigateTo('/pages/settings/ai-models/index')}>
              <Text className="menu-label">AI 模型管理</Text>
              <Text className="menu-arrow">›</Text>
            </View>
          </View>
        </View>

        <View className="menu-section">
          <Text className="section-title">关于</Text>
          <View className="menu-list">
            <View className="menu-item">
              <Text className="menu-label">版本号</Text>
              <Text className="menu-value">1.0.0</Text>
            </View>
          </View>
        </View>

        {/* 退出登录 */}
        <View className="logout-section">
          <View className="logout-btn" onClick={handleLogout}>
            <Text>退出登录</Text>
          </View>
        </View>
      </ScrollView>
    </View>
  )
}
