import { PropsWithChildren, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAuthStore } from '@/store/authStore'
import './app.scss'

function App({ children }: PropsWithChildren) {
  const { checkAuth } = useAuthStore()

  useEffect(() => {
    // 应用启动时检查认证状态
    checkAuth()
  }, [checkAuth])

  // 监听网络状态
  useEffect(() => {
    Taro.onNetworkStatusChange((res) => {
      if (!res.isConnected) {
        Taro.showToast({
          title: '网络连接已断开',
          icon: 'none',
          duration: 2000,
        })
      }
    })

    return () => {
      Taro.offNetworkStatusChange(() => {})
    }
  }, [])

  return children
}

export default App
