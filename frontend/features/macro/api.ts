import api from "@/shared/api/client";

export interface MacroTopic {
  id: string;
  title: string;
  summary: string;
  heat_score: number;
  impact_analysis: {
    logic: string;
    beneficiaries: { ticker: string; reason: string }[];
    detriments: { ticker: string; reason: string }[];
  };
  source_links: string[];
  updated_at: string;
}

interface MacroRadarItem {
  id?: string;
  title: string;
  summary?: string;
  heat_score?: number;
  impact_analysis?: {
    logic?: string;
    beneficiaries?: { ticker?: string; reason?: string }[];
    detriments?: { ticker?: string; reason?: string }[];
  };
  source_links?: string[];
  updated_at?: string;
  [key: string]: unknown;
}

export interface ClsNewsItem {
  title: string;
  content: string;
  time: string;
  [key: string]: unknown;
}

export async function getMacroRadar(refresh = false): Promise<MacroTopic[]> {
  const response = await api.get(`/api/v1/macro/radar?refresh=${refresh}`);
  const items = response.data as MacroRadarItem[];
  return items.map((item, index) => ({
    id: String(item.id ?? `${item.title}-${index}`),
    title: item.title,
    summary: typeof item.summary === "string" ? item.summary : "",
    heat_score: typeof item.heat_score === "number" ? item.heat_score : 0,
    impact_analysis: {
      logic: item.impact_analysis?.logic || "",
      beneficiaries: (item.impact_analysis?.beneficiaries || []).map((beneficiary) => ({
        ticker: beneficiary.ticker || "",
        reason: beneficiary.reason || "",
      })),
      detriments: (item.impact_analysis?.detriments || []).map((detriment) => ({
        ticker: detriment.ticker || "",
        reason: detriment.reason || "",
      })),
    },
    source_links: Array.isArray(item.source_links) ? item.source_links.filter((link): link is string => typeof link === "string") : [],
    updated_at: typeof item.updated_at === "string" ? item.updated_at : new Date().toISOString(),
  }));
}

export async function getClsNews(refresh = false): Promise<ClsNewsItem[]> {
  // Add timestamp to prevent browser caching on manual refresh
  const timestamp = refresh ? `&_t=${Date.now()}` : '';
  const response = await api.get(`/api/v1/macro/cls_news?refresh=${refresh}${timestamp}`);
  const items = response.data as ClsNewsItem[];
  return items.map((item) => ({
    title: item.title,
    content: typeof item.content === "string" ? item.content : "",
    time: typeof item.time === "string" ? item.time : "",
  }));
}
