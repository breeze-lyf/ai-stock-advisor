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

export async function getSectorExposure(): Promise<SectorExposureData> {
  const response = await api.get("/api/v1/portfolio/risk/sector-exposure");
  return response.data.data as SectorExposureData;
}
