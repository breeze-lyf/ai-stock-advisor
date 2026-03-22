import { View, Text, Input, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useCallback } from 'react'
import { httpClient } from '@/services'
import './password.scss'

export default function PasswordPage() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = useCallback(async () => {
    if (!oldPassword) {
      Taro.showToast({ title: '请输入原密码', icon: 'none' })
      return
    }
    if (!newPassword) {
      Taro.showToast({ title: '请输入新密码', icon: 'none' })
      return
    }
    if (newPassword.length < 6) {
      Taro.showToast({ title: '新密码至少6位', icon: 'none' })
      return
    }
    if (newPassword !== confirmPassword) {
      Taro.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    setIsLoading(true)
    try {
      await httpClient.put('/user/password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      Taro.showToast({ title: '密码修改成功', icon: 'success' })
      setTimeout(() => {
        Taro.navigateBack()
      }, 1500)
    } catch (error) {
      // 错误已在 httpClient 中处理
    } finally {
      setIsLoading(false)
    }
  }, [oldPassword, newPassword, confirmPassword])

  return (
    <View className="password-page">
      <View className="form">
        <View className="form-item">
          <Text className="form-label">原密码</Text>
          <Input
            className="form-input"
            password
            placeholder="请输入原密码"
            placeholderClass="input-placeholder"
            value={oldPassword}
            onInput={(e) => setOldPassword(e.detail.value)}
          />
        </View>

        <View className="form-item">
          <Text className="form-label">新密码</Text>
          <Input
            className="form-input"
            password
            placeholder="请输入新密码（至少6位）"
            placeholderClass="input-placeholder"
            value={newPassword}
            onInput={(e) => setNewPassword(e.detail.value)}
          />
        </View>

        <View className="form-item">
          <Text className="form-label">确认新密码</Text>
          <Input
            className="form-input"
            password
            placeholder="请再次输入新密码"
            placeholderClass="input-placeholder"
            value={confirmPassword}
            onInput={(e) => setConfirmPassword(e.detail.value)}
          />
        </View>

        <Button
          className={`submit-btn ${isLoading ? 'disabled' : ''}`}
          onClick={handleSubmit}
          disabled={isLoading}
        >
          {isLoading ? '提交中...' : '修改密码'}
        </Button>
      </View>
    </View>
  )
}
