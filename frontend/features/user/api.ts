import type {
  PasswordChange,
  TestConnectionResponse,
  UserProfile,
  UserSettingsUpdate,
} from "@/types";
import api from "@/shared/api/client";

export type AIModelConfigItem = {
  key: string;
  display_name: string;
  provider_note?: string | null;
  model_id: string;
  base_url: string;
  has_api_key: boolean;
  masked_api_key?: string | null;
  is_active: boolean;
  is_builtin: boolean;
};

export type ProviderConfigItem = {
  provider_key: string;
  display_name: string;
  base_url: string;
  priority: number;
  is_active: boolean;
};

export type MarketDataSourceOption = {
  key: string;
  label: string;
  description: string;
  is_available: boolean;
  is_default: boolean;
};

export type MarketDataSourceConfig = {
  a_share: string;
  hk_share: string;
  us_share: string;
};

export type DataSourceSettings = {
  config: MarketDataSourceConfig;
  available_sources: MarketDataSourceOption[];
};

export type DataSourceSettingsUpdate = {
  a_share?: string;
  hk_share?: string;
  us_share?: string;
};

export type NotificationRoutingSettings = {
  email_enabled: boolean;
  feishu_enabled: boolean;
  browser_push_enabled: boolean;
  sms_enabled: boolean;
  quiet_mode_enabled: boolean;
  quiet_mode_start?: string | null;
  quiet_mode_end?: string | null;
  p0_daily_limit: number;
  p1_daily_limit: number;
  p2_daily_limit: number;
  p3_daily_limit: number;
};

export type BrowserPushConfig = {
  web_push_enabled: boolean;
  vapid_public_key?: string | null;
};

export type BrowserPushSubscriptionItem = {
  id: string;
  device_name?: string | null;
  browser?: string | null;
  created_at: string;
  last_used_at?: string | null;
};

export type CreateAIModelConfigInput = {
  display_name: string;
  provider_note?: string;
  model_id: string;
  api_key?: string;
  base_url: string;
  key?: string;
  is_default?: boolean;
};

export async function getProfile(): Promise<UserProfile> {
  const response = await api.get("/api/v1/user/me");
  return response.data;
}

export async function updateSettings(settings: UserSettingsUpdate): Promise<UserProfile> {
  const response = await api.put("/api/v1/user/settings", settings);
  return response.data;
}

export async function testAIConnection(
  payload: {
    provider?: string;
    provider_note?: string;
    api_key?: string;
    base_url?: string;
    model_id?: string;
  }
): Promise<TestConnectionResponse> {
  const response = await api.post("/api/v1/user/test-connection", payload);
  return response.data;
}

export async function testTavilyConnection(payload?: { api_key?: string }): Promise<TestConnectionResponse> {
  const response = await api.post("/api/v1/user/test-tavily", payload || {});
  return response.data;
}

export async function testFeishuWebhook(payload?: { webhook_url?: string }): Promise<TestConnectionResponse> {
  const response = await api.post("/api/v1/user/test-feishu-webhook", payload || {});
  return response.data;
}

export async function changePassword(data: PasswordChange) {
  const response = await api.put("/api/v1/user/password", data);
  return response.data;
}

export async function listAIModels(): Promise<AIModelConfigItem[]> {
  const response = await api.get("/api/v1/user/ai-models");
  return response.data;
}

export async function createAIModel(input: CreateAIModelConfigInput): Promise<AIModelConfigItem> {
  const response = await api.post("/api/v1/user/ai-models", input);
  return response.data;
}

export async function listProviders(): Promise<ProviderConfigItem[]> {
  const response = await api.get("/api/v1/user/providers");
  return response.data;
}

export async function getDataSourceSettings(): Promise<DataSourceSettings> {
  const response = await api.get("/api/v1/user/data-sources");
  return response.data;
}

export async function updateDataSourceSettings(
  settings: DataSourceSettingsUpdate
): Promise<{ status: string; message: string }> {
  const response = await api.put("/api/v1/user/data-sources", settings);
  return response.data;
}

export async function listMarketDataSources(): Promise<MarketDataSourceOption[]> {
  const response = await api.get("/api/v1/user/market-data-sources");
  return response.data;
}

export async function deleteAIModel(modelKey: string): Promise<{ status: string; message: string }> {
  const response = await api.delete(`/api/v1/user/ai-models/${encodeURIComponent(modelKey)}`);
  return response.data;
}

export async function testDataSource(provider: string): Promise<TestConnectionResponse> {
  const response = await api.post("/api/v1/user/data-sources/test", { provider });
  return response.data;
}

export async function getNotificationRoutingSettings(): Promise<NotificationRoutingSettings> {
  const response = await api.get("/api/v1/notification-settings/notification-settings");
  return response.data.settings;
}

export async function updateNotificationRoutingSettings(
  settings: Partial<NotificationRoutingSettings>
): Promise<NotificationRoutingSettings> {
  const params = new URLSearchParams();
  Object.entries(settings).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const suffix = params.toString();
  const response = await api.patch(
    `/api/v1/notification-settings/notification-settings${suffix ? `?${suffix}` : ""}`
  );
  return response.data.settings;
}

export async function testNotificationRouting(priority: "P0" | "P1" | "P2" | "P3"): Promise<{
  status: string;
  result: {
    sent_channels: string[];
    skipped_channels: string[];
    blocked_reason: string | null;
  };
}> {
  const response = await api.post(`/api/v1/notification-settings/notification-settings/test?priority=${priority}`);
  return response.data;
}

export async function getBrowserPushConfig(): Promise<BrowserPushConfig> {
  const response = await api.get("/api/v1/notification-settings/notification-settings/browser-push/config");
  return response.data.config;
}

export async function getBrowserPushSubscriptions(): Promise<BrowserPushSubscriptionItem[]> {
  const response = await api.get("/api/v1/notification-settings/notification-settings/browser-push");
  return response.data.subscriptions;
}

export async function subscribeBrowserPush(payload: {
  endpoint: string;
  p256dh: string;
  auth: string;
  device_name?: string;
  browser?: string;
}): Promise<{ status: string; subscription: BrowserPushSubscriptionItem }> {
  const params = new URLSearchParams();
  params.set("endpoint", payload.endpoint);
  params.set("p256dh", payload.p256dh);
  params.set("auth", payload.auth);
  if (payload.device_name) params.set("device_name", payload.device_name);
  if (payload.browser) params.set("browser", payload.browser);
  const response = await api.post(`/api/v1/notification-settings/notification-settings/browser-push/subscribe?${params.toString()}`);
  return response.data;
}

export async function unsubscribeBrowserPush(subscriptionId: string): Promise<{ status: string }> {
  const response = await api.delete(`/api/v1/notification-settings/notification-settings/browser-push/${subscriptionId}`);
  return response.data;
}

export async function unsubscribeBrowserPushByEndpoint(endpoint: string): Promise<{ status: string }> {
  const params = new URLSearchParams();
  params.set("endpoint", endpoint);
  const response = await api.delete(`/api/v1/notification-settings/notification-settings/browser-push?${params.toString()}`);
  return response.data;
}

// User Preferences & Onboarding
export type InvestmentProfile = "CONSERVATIVE" | "BALANCED" | "AGGRESSIVE";
export type MarketPreference = "A_SHARE" | "HK_SHARE" | "US_SHARE";
export type NotificationFrequency = "REALTIME" | "HOURLY" | "DAILY" | "NEVER";

export type UserPreferenceResponse = {
  investment_profile: string;
  preferred_markets: string[];
  notification_frequency: string;
  onboarding_completed: boolean;
  risk_tolerance_score: number;
  investment_experience_years: number;
  target_annual_return: number;
};

export type OnboardingRequest = {
  investment_profile: InvestmentProfile;
  preferred_markets: MarketPreference[];
  notification_frequency: NotificationFrequency;
  risk_tolerance_score: number;
  investment_experience_years: number;
  target_annual_return: number;
};

export async function getUserPreferences(): Promise<UserPreferenceResponse> {
  const response = await api.get("/api/v1/user-preferences/preferences");
  return response.data;
}

export async function completeOnboarding(payload: OnboardingRequest): Promise<{ success: boolean; message: string; onboarding_completed: boolean }> {
  const response = await api.post("/api/v1/user-preferences/onboarding", payload);
  return response.data;
}

export async function updateUserPreferences(payload: Partial<OnboardingRequest>): Promise<UserPreferenceResponse> {
  const response = await api.patch("/api/v1/user-preferences/preferences", payload, {
    params: payload,
  });
  return response.data;
}
