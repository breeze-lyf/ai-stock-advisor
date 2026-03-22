import Taro from '@tarojs/taro'

// API 基础配置
function resolveApiBaseUrl(): string {
  const configured =
    process.env.TARO_APP_API_BASE_URL ||
    process.env.TARO_APP_API_URL ||
    'http://localhost:8000'

  return configured.replace(/\/+$/, '').replace(/\/api\/v1$/i, '')
}

const API_BASE_URL = `${resolveApiBaseUrl()}/api/v1`

interface RequestConfig {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  data?: unknown
  headers?: Record<string, string>
  showError?: boolean
}

interface ApiResponse<T = unknown> {
  data: T
  statusCode: number
}

class HttpClient {
  private baseUrl: string
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private getToken(): string | null {
    try {
      const res = Taro.getStorageSync('auth_token')
      return res || null
    } catch {
      return null
    }
  }

  private async request<T>(config: RequestConfig): Promise<T> {
    const { url, method = 'GET', data, headers = {}, showError = true } = config
    const token = this.getToken()
    
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    }
    
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`
    }

    try {
      const response = await Taro.request({
        url: `${this.baseUrl}${url}`,
        method,
        data,
        header: requestHeaders,
      }) as ApiResponse<T>

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return response.data
      }

      // 处理认证错误
      if (response.statusCode === 401) {
        // Token 过期，清除本地存储并跳转登录
        Taro.removeStorageSync('auth_token')
        Taro.removeStorageSync('auth_user')
        Taro.reLaunch({ url: '/pages/login/index' })
        throw new Error('登录已过期，请重新登录')
      }

      // 处理其他错误
      const errorData = response.data as { detail?: string; message?: string }
      const errorMessage = errorData?.detail || errorData?.message || '请求失败'
      
      if (showError) {
        Taro.showToast({
          title: errorMessage,
          icon: 'none',
          duration: 2000,
        })
      }
      
      throw new Error(errorMessage)
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      
      // 网络错误
      const message = '网络连接失败，请检查网络'
      if (showError) {
        Taro.showToast({
          title: message,
          icon: 'none',
          duration: 2000,
        })
      }
      throw new Error(message)
    }
  }

  get<T>(url: string, config?: Omit<RequestConfig, 'url' | 'method'>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'GET' })
  }

  post<T>(url: string, data?: unknown, config?: Omit<RequestConfig, 'url' | 'method' | 'data'>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'POST', data })
  }

  put<T>(url: string, data?: unknown, config?: Omit<RequestConfig, 'url' | 'method' | 'data'>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'PUT', data })
  }

  delete<T>(url: string, config?: Omit<RequestConfig, 'url' | 'method'>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'DELETE' })
  }
}

export const httpClient = new HttpClient(API_BASE_URL)
export default httpClient
