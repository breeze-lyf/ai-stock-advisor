import { View, Text, Input, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import './index.scss'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuthStore()

  const handleLogin = useCallback(async () => {
    if (!email.trim()) {
      Taro.showToast({ title: '请输入邮箱', icon: 'none' })
      return
    }
    if (!password) {
      Taro.showToast({ title: '请输入密码', icon: 'none' })
      return
    }

    const success = await login(email.trim(), password)
    if (success) {
      Taro.showToast({ title: '登录成功', icon: 'success' })
      Taro.switchTab({ url: '/pages/index/index' })
    }
  }, [email, password, login])

  const goToRegister = useCallback(() => {
    clearError()
    Taro.navigateTo({ url: '/pages/register/index' })
  }, [clearError])

  return (
    <View className="login-page">
      <View className="login-header">
        <Text className="login-title">AI 智能投顾</Text>
        <Text className="login-subtitle">您的专属投资分析助手</Text>
      </View>

      <View className="login-form">
        <View className="form-item">
          <Text className="form-label">邮箱</Text>
          <Input
            className="form-input"
            type="text"
            placeholder="请输入邮箱地址"
            placeholderClass="input-placeholder"
            value={email}
            onInput={(e) => setEmail(e.detail.value)}
          />
        </View>

        <View className="form-item">
          <Text className="form-label">密码</Text>
          <Input
            className="form-input"
            password
            placeholder="请输入密码"
            placeholderClass="input-placeholder"
            value={password}
            onInput={(e) => setPassword(e.detail.value)}
          />
        </View>

        {error && (
          <View className="error-message">
            <Text>{error}</Text>
          </View>
        )}

        <Button
          className={`login-btn ${isLoading ? 'btn-disabled' : ''}`}
          onClick={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? '登录中...' : '登录'}
        </Button>

        <View className="register-link" onClick={goToRegister}>
          <Text>还没有账号？</Text>
          <Text className="link-text">立即注册</Text>
        </View>
      </View>

      <View className="login-footer">
        <Text className="footer-text">登录即表示同意服务条款和隐私政策</Text>
      </View>
    </View>
  )
}
