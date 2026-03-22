import { View, Text, Input, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import './index.scss'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const { register, isLoading, error, clearError } = useAuthStore()

  const handleRegister = useCallback(async () => {
    if (!email.trim()) {
      Taro.showToast({ title: '请输入邮箱', icon: 'none' })
      return
    }
    if (!password) {
      Taro.showToast({ title: '请输入密码', icon: 'none' })
      return
    }
    if (password.length < 6) {
      Taro.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }
    if (password !== confirmPassword) {
      Taro.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    const success = await register(email.trim(), password)
    if (success) {
      Taro.showToast({ title: '注册成功', icon: 'success' })
      Taro.switchTab({ url: '/pages/index/index' })
    }
  }, [email, password, confirmPassword, register])

  const goToLogin = useCallback(() => {
    clearError()
    Taro.navigateBack()
  }, [clearError])

  return (
    <View className="register-page">
      <View className="register-header">
        <Text className="register-title">创建账号</Text>
        <Text className="register-subtitle">开启您的智能投资之旅</Text>
      </View>

      <View className="register-form">
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
            placeholder="请输入密码（至少6位）"
            placeholderClass="input-placeholder"
            value={password}
            onInput={(e) => setPassword(e.detail.value)}
          />
        </View>

        <View className="form-item">
          <Text className="form-label">确认密码</Text>
          <Input
            className="form-input"
            password
            placeholder="请再次输入密码"
            placeholderClass="input-placeholder"
            value={confirmPassword}
            onInput={(e) => setConfirmPassword(e.detail.value)}
          />
        </View>

        {error && (
          <View className="error-message">
            <Text>{error}</Text>
          </View>
        )}

        <Button
          className={`register-btn ${isLoading ? 'btn-disabled' : ''}`}
          onClick={handleRegister}
          disabled={isLoading}
        >
          {isLoading ? '注册中...' : '注册'}
        </Button>

        <View className="login-link" onClick={goToLogin}>
          <Text>已有账号？</Text>
          <Text className="link-text">返回登录</Text>
        </View>
      </View>
    </View>
  )
}
