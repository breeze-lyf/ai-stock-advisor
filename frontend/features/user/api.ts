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

export async function deleteAIModel(modelKey: string): Promise<{ status: string; message: string }> {
  const response = await api.delete(`/api/v1/user/ai-models/${encodeURIComponent(modelKey)}`);
  return response.data;
}
