import Taro from '@tarojs/taro'

function resolveApiBaseUrl(): string {
  const configured =
    process.env.TARO_APP_API_BASE_URL ||
    process.env.TARO_APP_API_URL ||
    'http://localhost:8000'

  return configured.replace(/\/+$/, '').replace(/\/api\/v1$/i, '')
}

const API_BASE_URL = `${resolveApiBaseUrl()}/api/v1`

interface LoginResponse {
  access_token: string
  token_type: string
}

interface User {
  id: string
  email: string
  username?: string
}

export const authApi = {
  /**
   * 用户登录
   */
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await Taro.request({
      url: `${API_BASE_URL}/auth/login`,
      method: 'POST',
      header: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      data: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
    })

    if (response.statusCode !== 200) {
      const errorData = response.data as { detail?: string }
      throw new Error(errorData?.detail || '登录失败')
    }

    return response.data as LoginResponse
  },

  /**
   * 用户注册
   */
  register: async (email: string, password: string): Promise<User> => {
    const response = await Taro.request({
      url: `${API_BASE_URL}/auth/register`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
      },
      data: { email, password },
    })

    if (response.statusCode !== 200 && response.statusCode !== 201) {
      const errorData = response.data as { detail?: string }
      throw new Error(errorData?.detail || '注册失败')
    }

    return response.data as User
  },

  /**
   * 获取当前用户信息
   */
  getMe: async (token: string): Promise<User> => {
    const response = await Taro.request({
      url: `${API_BASE_URL}/user/me`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (response.statusCode !== 200) {
      throw new Error('获取用户信息失败')
    }

    return response.data as User
  },
}

export default authApi
