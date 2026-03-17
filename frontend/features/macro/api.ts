import api from "@/shared/api/client";

export async function getMacroRadar(refresh = false): Promise<any[]> {
  const response = await api.get(`/api/v1/macro/radar?refresh=${refresh}`);
  return response.data;
}

export async function getClsNews(refresh = false): Promise<any[]> {
  const response = await api.get(`/api/v1/macro/cls_news?refresh=${refresh}`);
  return response.data;
}
