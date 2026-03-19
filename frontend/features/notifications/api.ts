import api from "@/shared/api/client";

export interface NotificationLog {
  id: string;
  type: string;
  title: string;
  content: string;
  card_payload: unknown;
  created_at: string;
}

export async function getNotificationHistory(limit = 30): Promise<NotificationLog[]> {
  const response = await api.get(`/api/v1/notifications/history?limit=${limit}`);
  return response.data;
}
