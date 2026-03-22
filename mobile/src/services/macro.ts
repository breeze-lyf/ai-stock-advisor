import httpClient from './client'

export interface MacroRadarItem {
  id: string
  title: string
  summary: string
  heat_score: number
  updated_at: string
  impact_analysis?: {
    logic?: string
    beneficiaries?: Array<{ ticker: string; reason: string }>
    detriments?: Array<{ ticker: string; reason: string }>
  }
}

export interface GlobalNews {
  time: string
  title: string
  content: string
}

export interface MacroRadarResponse {
  items: MacroRadarItem[]
  summary: string
  updated_at: string
}

interface MacroRadarApiItem {
  id: string
  title: string
  summary?: string | null
  heat_score?: number | null
  updated_at?: string | null
  impact_analysis?: {
    logic?: string
    beneficiaries?: Array<{ ticker?: string; reason?: string }>
    detriments?: Array<{ ticker?: string; reason?: string }>
  } | null
}

export const macroApi = {
  /**
   * 获取宏观雷达数据
   */
  getMacroRadar: async (): Promise<MacroRadarResponse> => {
    const items = await httpClient.get<MacroRadarApiItem[]>('/macro/radar')
    const normalizedItems: MacroRadarItem[] = items.map((item) => ({
      id: item.id,
      title: item.title,
      summary: item.summary || '',
      heat_score: item.heat_score ?? 0,
      updated_at: item.updated_at || new Date().toISOString(),
      impact_analysis: item.impact_analysis
        ? {
            logic: item.impact_analysis.logic || '',
            beneficiaries: (item.impact_analysis.beneficiaries || []).map((entry) => ({
              ticker: entry.ticker || '',
              reason: entry.reason || '',
            })),
            detriments: (item.impact_analysis.detriments || []).map((entry) => ({
              ticker: entry.ticker || '',
              reason: entry.reason || '',
            })),
          }
        : undefined,
    }))

    return {
      items: normalizedItems,
      summary: normalizedItems[0]?.summary || '',
      updated_at: normalizedItems[0]?.updated_at || new Date().toISOString(),
    }
  },

  /**
   * 获取财联社新闻
   */
  getClsNews: async (limit = 20): Promise<GlobalNews[]> => {
    return httpClient.get<GlobalNews[]>(`/macro/cls_news?limit=${limit}`)
  },
}

export default macroApi
