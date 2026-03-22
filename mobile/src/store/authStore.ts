import { create } from 'zustand'
import Taro from '@tarojs/taro'
import { authApi } from '@/services/auth'

interface User {
  id: string
  email: string
  username?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>
  register: (email: string, password: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<void>
  clearError: () => void
}

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authApi.login(email, password)
      const { access_token } = response
      
      // 保存 token 到本地存储
      await Taro.setStorage({ key: TOKEN_KEY, data: access_token })
      
      // 获取用户信息
      const user = await authApi.getMe(access_token)
      await Taro.setStorage({ key: USER_KEY, data: JSON.stringify(user) })
      
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      })
      return true
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '登录失败，请重试'
      set({ error: message, isLoading: false })
      return false
    }
  },

  register: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      await authApi.register(email, password)
      // 注册成功后自动登录
      return await get().login(email, password)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '注册失败，请重试'
      set({ error: message, isLoading: false })
      return false
    }
  },

  logout: () => {
    Taro.removeStorage({ key: TOKEN_KEY })
    Taro.removeStorage({ key: USER_KEY })
    set({
      user: null,
      token: null,
      isAuthenticated: false,
    })
    // 跳转到登录页
    Taro.reLaunch({ url: '/pages/login/index' })
  },

  checkAuth: async () => {
    try {
      const tokenRes = await Taro.getStorage({ key: TOKEN_KEY })
      const userRes = await Taro.getStorage({ key: USER_KEY })
      
      if (tokenRes.data && userRes.data) {
        const user = JSON.parse(userRes.data)
        set({
          token: tokenRes.data,
          user,
          isAuthenticated: true,
        })
      }
    } catch {
      // 没有存储的认证信息，保持未登录状态
      set({ isAuthenticated: false })
    }
  },

  clearError: () => set({ error: null }),
}))
