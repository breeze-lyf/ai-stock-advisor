import httpClient from './client'

// 通知日志类型
export interface NotificationLog {
  id: string
  type: 'MACRO_ALERT' | 'PRICE_ALERT' | 'DAILY_REPORT' | 'INDICATOR_ALERT' | string
  title: string
  content: string
  card_payload: unknown
  created_at: string
}

export const alertsApi = {
  /**
   * 获取通知历史记录
   */
  getNotificationHistory: async (limit = 30): Promise<NotificationLog[]> => {
    return httpClient.get<NotificationLog[]>(`/notifications/history?limit=${limit}`)
  },
}

export default alertsApi
