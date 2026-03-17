import type { NotificationLog } from "@/features/notifications/api";
import type { MacroTopic } from "@/features/dashboard/hooks/useDashboardRadarData";
import type {
  AnalysisResponse,
  PortfolioAnalysisResponse,
  PortfolioItem,
  PortfolioSummary,
  SimulatedTrade,
  UserProfile,
} from "@/types";

export type CacheValue<T> = T | null;

export interface DashboardCacheEntry<T> {
  ttlMs: number;
  updatedAt: number | null;
  value: CacheValue<T>;
}

export function createDashboardCacheEntry<T>(ttlMs: number): DashboardCacheEntry<T> {
  return {
    ttlMs,
    updatedAt: null,
    value: null,
  };
}

export function getOrCreateDashboardCacheEntry<T>(
  store: Record<string, DashboardCacheEntry<T>>,
  key: string,
  ttlMs: number
): DashboardCacheEntry<T> {
  if (!store[key]) {
    store[key] = createDashboardCacheEntry<T>(ttlMs);
  }
  return store[key];
}

export function readDashboardCache<T>(entry: DashboardCacheEntry<T>): CacheValue<T> {
  return entry.value;
}

export function writeDashboardCache<T>(entry: DashboardCacheEntry<T>, value: CacheValue<T>): CacheValue<T> {
  entry.value = value;
  entry.updatedAt = Date.now();
  return value;
}

export function hasDashboardCache<T>(entry: DashboardCacheEntry<T>): boolean {
  return entry.value !== null;
}

export function isDashboardCacheStale<T>(entry: DashboardCacheEntry<T>): boolean {
  if (!hasDashboardCache(entry) || entry.updatedAt === null) {
    return true;
  }
  return Date.now() - entry.updatedAt > entry.ttlMs;
}

export function shouldRevalidateDashboardCache<T>(entry: DashboardCacheEntry<T>): boolean {
  return !hasDashboardCache(entry) || isDashboardCacheStale(entry);
}

export const dashboardCache = {
  alerts: {
    logs: createDashboardCacheEntry<NotificationLog[]>(30_000),
  },
  analysis: {
    byTicker: {} as Record<string, DashboardCacheEntry<AnalysisResponse>>,
    historyByTicker: {} as Record<string, DashboardCacheEntry<AnalysisResponse[]>>,
    newsByTicker: {} as Record<string, DashboardCacheEntry<Record<string, unknown>[]>>,
  },
  market: {
    historyByTicker: {} as Record<string, DashboardCacheEntry<unknown[]>>,
  },
  paperTrading: {
    trades: createDashboardCacheEntry<SimulatedTrade[]>(60_000),
  },
  portfolio: {
    items: createDashboardCacheEntry<PortfolioItem[]>(60_000),
    user: createDashboardCacheEntry<UserProfile>(5 * 60_000),
  },
  portfolioTab: {
    analysis: createDashboardCacheEntry<PortfolioAnalysisResponse>(10 * 60_000),
    summary: createDashboardCacheEntry<PortfolioSummary>(60_000),
  },
  radar: {
    topics: createDashboardCacheEntry<MacroTopic[]>(5 * 60_000),
  },
};
