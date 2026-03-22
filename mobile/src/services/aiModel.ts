import httpClient from './client'

// AI 模型配置类型
export interface AIModelConfigItem {
  key: string
  display_name: string
  provider_note?: string | null
  model_id: string
  base_url: string
  has_api_key: boolean
  masked_api_key?: string | null
  is_active: boolean
  is_builtin: boolean
}

export interface CreateAIModelInput {
  display_name: string
  provider_note?: string
  model_id: string
  api_key?: string
  base_url: string
  key?: string
  is_default?: boolean
}

export interface TestConnectionResponse {
  status: 'success' | 'error'
  message: string
}

export const aiModelApi = {
  /**
   * 获取所有 AI 模型列表
   */
  listModels: async (): Promise<AIModelConfigItem[]> => {
    return httpClient.get<AIModelConfigItem[]>('/user/ai-models')
  },

  /**
   * 创建或更新 AI 模型
   */
  createModel: async (input: CreateAIModelInput): Promise<AIModelConfigItem> => {
    return httpClient.post<AIModelConfigItem>('/user/ai-models', input)
  },

  /**
   * 删除 AI 模型
   */
  deleteModel: async (modelKey: string): Promise<{ status: string; message: string }> => {
    return httpClient.delete<{ status: string; message: string }>(`/user/ai-models/${encodeURIComponent(modelKey)}`)
  },

  /**
   * 测试 AI 模型连接
   */
  testConnection: async (payload: {
    provider_note?: string
    model_id: string
    api_key?: string
    base_url: string
  }): Promise<TestConnectionResponse> => {
    return httpClient.post<TestConnectionResponse>('/user/test-connection', payload)
  },
}

export default aiModelApi
