import api from "@/shared/api/client";

export interface SectorBreakdown {
  sector: string;
  value: number;
  weight: number;
}

export interface SectorExposureData {
  total_value: number;
  sector_breakdown: SectorBreakdown[];
  concentration_ratio: number;
  herfindahl_index: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
}

export interface PositionImpactSectorRow {
  sector: string;
  value: number;
  weight: number;
}

export interface PositionImpactAnalysis {
  current_sector_exposure: PositionImpactSectorRow[];
  projected_sector_exposure: PositionImpactSectorRow[];
  current_beta: number;
  projected_beta: number;
  current_sharpe: number;
  projected_sharpe: number;
  max_recommended_pct: number;
  ai_suggestion: string;
  warnings: string[];
}

export async function getSectorExposure(): Promise<SectorExposureData> {
  const response = await api.get("/api/v1/portfolio/risk/sector-exposure");
  return response.data.data as SectorExposureData;
}

export async function getPositionImpactAnalysis(
  ticker: string,
  positionPct: number,
): Promise<PositionImpactAnalysis> {
  const params = new URLSearchParams({
    ticker,
    position_pct: String(positionPct),
  });
  const response = await api.get(`/api/v1/portfolio/risk/impact-analysis?${params.toString()}`);
  return response.data.data as PositionImpactAnalysis;
}
