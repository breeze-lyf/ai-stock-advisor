"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import {
  ArrowLeft,
  Bell,
  Bot,
  ChevronRight,
  HardDrive,
  Moon,
  Pencil,
  Plus,
  RefreshCcw,
  Save,
  Settings2,
  Shield,
  Sparkles,
  Sun,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  changePassword,
  createAIModel,
  deleteAIModel,
  getProfile,
  listMarketDataSources,
  listAIModels,
  testAIConnection,
  testTavilyConnection,
  updateSettings,
  type AIModelConfigItem,
  type CreateAIModelConfigInput,
  type MarketDataSourceOption,
} from "@/features/user/api";
import type { UserProfile } from "@/types";

type SettingsSection = "general" | "ai" | "notifications" | "security" | "data";

const SECTION_ITEMS: Array<{ id: SettingsSection; label: string; description: string; icon: typeof Settings2 }> = [
  { id: "general", label: "通用设置", description: "主题与时区", icon: Settings2 },
  { id: "ai", label: "AI 配置", description: "默认模型与我的模型", icon: Bot },
  { id: "notifications", label: "通知", description: "飞书与推送偏好", icon: Bell },
  { id: "security", label: "安全", description: "密码管理", icon: Shield },
  { id: "data", label: "数据管理", description: "配置状态与同步", icon: HardDrive },
];

function normalizeBaseUrl(rawBaseUrl?: string) {
  const trimmed = (rawBaseUrl || "").trim();
  if (!trimmed) return "";
  return trimmed.replace(/\/+$/, "").replace(/\/chat\/completions$/i, "").replace(/\/models$/i, "");
}

function maskText(value: string, keep = 40) {
  if (value.length <= keep) return value;
  return `${value.slice(0, keep)}...`;
}

export default function SettingsPage() {
  const { token, user: authUser, isAuthenticated, loading: authLoading } = useAuth();
  const { theme: currentTheme, setTheme } = useTheme();

  const [mounted, setMounted] = useState(false);
  const [activeSection, setActiveSection] = useState<SettingsSection>("general");
  const [profile, setProfile] = useState<UserProfile | null>(authUser);
  const [profileLoading, setProfileLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const [availableModels, setAvailableModels] = useState<AIModelConfigItem[]>([]);
  const [availableDataSources, setAvailableDataSources] = useState<MarketDataSourceOption[]>([]);
  const [, setModelsLoading] = useState(false);
  const [isAddModelOpen, setIsAddModelOpen] = useState(false);
  const [addingModel, setAddingModel] = useState(false);
  const [testingModel, setTestingModel] = useState(false);
  const [deletingModelKey, setDeletingModelKey] = useState<string | null>(null);
  const [editingModelKey, setEditingModelKey] = useState<string | null>(null);
  const [modelTestMessage, setModelTestMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [customModel, setCustomModel] = useState({
    key: "",
    display_name: "",
    provider_note: "",
    model_id: "",
    api_key: "",
    base_url: "",
    is_default: false,
  });

  const [feishuUrl, setFeishuUrl] = useState("");
  const [tavilyApiKey, setTavilyApiKey] = useState("");
  const [tavilyEnabled, setTavilyEnabled] = useState(true);
  const [hasSavedTavilyKey, setHasSavedTavilyKey] = useState(false);
  const [testingTavily, setTestingTavily] = useState(false);
  const [tavilyTestMessage, setTavilyTestMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [passwordForm, setPasswordForm] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    setMounted(true);
    if (!authUser) return;
    setProfile(authUser);
    setFeishuUrl(authUser.feishu_webhook_url || "");
    const tavilyCredential = authUser.provider_credentials?.tavily;
    setHasSavedTavilyKey(Boolean(tavilyCredential?.has_key));
    setTavilyEnabled(tavilyCredential?.is_enabled ?? true);
    setTavilyApiKey("");
    if (authUser.theme && currentTheme !== authUser.theme) setTheme(authUser.theme);
  }, [authUser, currentTheme, setTheme]);

  const loadProfile = useCallback(async () => {
    setProfileLoading(true);
    try {
      const data = await getProfile();
      setProfile(data);
      setFeishuUrl(data.feishu_webhook_url || "");
      const tavilyCredential = data.provider_credentials?.tavily;
      setHasSavedTavilyKey(Boolean(tavilyCredential?.has_key));
      setTavilyEnabled(tavilyCredential?.is_enabled ?? true);
      setTavilyApiKey("");
      if (data.theme && currentTheme !== data.theme) setTheme(data.theme);
    } catch (error) {
      console.error("Failed to load profile", error);
    } finally {
      setProfileLoading(false);
    }
  }, [currentTheme, setTheme]);

  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      setAvailableModels(await listAIModels());
    } catch (error) {
      console.error("Failed to load AI models", error);
      setAvailableModels([]);
    } finally {
      setModelsLoading(false);
    }
  }, []);

  const loadDataSources = useCallback(async () => {
    try {
      setAvailableDataSources(await listMarketDataSources());
    } catch (error) {
      console.error("Failed to load market data sources", error);
      setAvailableDataSources([]);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!token && !isAuthenticated) {
      return;
    }
    void loadProfile();
    void loadModels();
    void loadDataSources();
  }, [authLoading, isAuthenticated, loadDataSources, loadModels, loadProfile, token]);

  const selectedModel = useMemo(
    () => availableModels.find((model) => model.key === (profile?.preferred_ai_model || "")) || null,
    [availableModels, profile?.preferred_ai_model],
  );

  const selectedDataSource = useMemo(
    () => availableDataSources.find((item) => item.key === (profile?.preferred_data_source || "AKSHARE")) || null,
    [availableDataSources, profile?.preferred_data_source],
  );

  const handleSetDefaultModel = async (modelKey: string) => {
    setSaving(true);
    setMessage(null);
    try {
      await updateSettings({ preferred_ai_model: modelKey });
      await loadProfile();
      setMessage({ text: "默认分析模型已更新。", type: "success" });
    } catch (error) {
      console.error("Failed to update default model", error);
      setMessage({ text: "切换默认模型失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleAddModel = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingModel(true);
    setMessage(null);

    const payload: CreateAIModelConfigInput = {
      key: customModel.key.trim() || undefined,
      display_name: customModel.display_name.trim(),
      provider_note: customModel.provider_note.trim() || undefined,
      model_id: customModel.model_id.trim(),
      api_key: customModel.api_key.trim() || undefined,
      base_url: normalizeBaseUrl(customModel.base_url),
      is_default: customModel.is_default,
    };

    if (!payload.display_name || !payload.model_id || !payload.base_url) {
      setMessage({ text: "请填写模型名称、模型名称标识和 Base URL。", type: "error" });
      setAddingModel(false);
      return;
    }
    if (!editingModelKey && !payload.api_key) {
      setMessage({ text: "新增模型时必须填写 API Key。", type: "error" });
      setAddingModel(false);
      return;
    }

    try {
      const savedModel = await createAIModel(payload);
      
      // 1. Update models list immediately
      setAvailableModels((prev) => [savedModel, ...prev.filter((item) => item.key !== savedModel.key)]);
      
      // 2. Optimistic Profile Update & Non-blocking Settings Update
      const needsProfileUpdate = customModel.is_default && profile?.preferred_ai_model !== savedModel.key;
      
      if (needsProfileUpdate) {
        // Fire and forget settings update
        updateSettings({ preferred_ai_model: savedModel.key }).catch(err => {
          console.error("Failed to update preferred model:", err);
        });
        
        // Optimistically update local profile
        if (profile) {
          setProfile({ ...profile, preferred_ai_model: savedModel.key });
        }
      }

      // 3. Immediate UI Reset
      setCustomModel({
        key: "",
        display_name: "",
        provider_note: "",
        model_id: "",
        api_key: "",
        base_url: "",
        is_default: false,
      });
      setEditingModelKey(null);
      setModelTestMessage(null);
      setIsAddModelOpen(false);
      
      setMessage({ 
        text: editingModelKey 
          ? `模型 ${savedModel.display_name} 已更新。` 
          : (customModel.is_default ? `模型 ${savedModel.display_name} 已添加并设为默认。` : `模型 ${savedModel.display_name} 已添加。`), 
        type: "success" 
      });

      // 4. Background sync if needed, but don't block UI closure
      if (needsProfileUpdate) {
          setTimeout(() => loadProfile(), 1000); // Debounced background sync
      }
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setMessage({ text: axiosErr.response?.data?.detail || (editingModelKey ? "更新模型失败。" : "添加模型失败。"), type: "error" });
    } finally {
      setAddingModel(false);
    }
  };

  const handleTestModel = async () => {
    setModelTestMessage(null);
    const payload = {
      provider_note: customModel.provider_note.trim() || undefined,
      model_id: customModel.model_id.trim(),
      api_key: customModel.api_key.trim() || undefined,
      base_url: normalizeBaseUrl(customModel.base_url),
    };

    if (!payload.model_id || !payload.base_url) {
      setModelTestMessage({ text: "测试前请先填写模型名称标识和 Base URL。", type: "error" });
      return;
    }
    if (!payload.api_key && !editingModelKey) {
      setModelTestMessage({ text: "测试前请先填写模型名称标识、API Key 和 Base URL。", type: "error" });
      return;
    }

    setTestingModel(true);
    try {
      const result = await testAIConnection(payload);
      setModelTestMessage({
        text: result.message,
        type: result.status === "success" ? "success" : "error",
      });
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setModelTestMessage({
        text: axiosErr.response?.data?.detail || "测试连接失败。",
        type: "error",
      });
    } finally {
      setTestingModel(false);
    }
  };

  const resetModelForm = () => {
    setCustomModel({
      key: "",
      display_name: "",
      provider_note: "",
      model_id: "",
      api_key: "",
      base_url: "",
      is_default: false,
    });
    setEditingModelKey(null);
    setModelTestMessage(null);
  };

  const openAddModelDialog = () => {
    resetModelForm();
    setIsAddModelOpen(true);
  };

  const openEditModelDialog = (model: AIModelConfigItem) => {
    setCustomModel({
      key: model.key,
      display_name: model.display_name,
      provider_note: model.provider_note || "",
      model_id: model.model_id,
      api_key: "",
      base_url: normalizeBaseUrl(model.base_url),
      is_default: profile?.preferred_ai_model === model.key,
    });
    setEditingModelKey(model.key);
    setModelTestMessage(null);
    setIsAddModelOpen(true);
  };

  const handleDeleteModel = async (modelKey: string) => {
    setDeletingModelKey(modelKey);
    setMessage(null);
    try {
      const response = await deleteAIModel(modelKey);
      setAvailableModels((prev) => prev.filter((model) => model.key !== modelKey));
      await loadProfile();
      setMessage({ text: response.message || "模型已删除。", type: "success" });
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setMessage({ text: axiosErr.response?.data?.detail || "删除模型失败。", type: "error" });
    } finally {
      setDeletingModelKey(null);
    }
  };

  const handleThemeUpdate = async (theme: string) => {
    setSaving(true);
    setTheme(theme);
    try {
      await updateSettings({ theme });
      await loadProfile();
      setMessage({ text: "外观主题已更新。", type: "success" });
    } catch (error) {
      console.error("Failed to update theme", error);
      setMessage({ text: "更新主题失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleTimezoneUpdate = async (timezone: string) => {
    setSaving(true);
    try {
      await updateSettings({ timezone });
      await loadProfile();
      setMessage({ text: "时区设置已更新。", type: "success" });
    } catch (error) {
      console.error("Failed to update timezone", error);
      setMessage({ text: "更新时区失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleSwitch = async (key: keyof UserProfile, value: boolean) => {
    setSaving(true);
    try {
      await updateSettings({ [key]: value });
      await loadProfile();
      setMessage({ text: "通知偏好已更新。", type: "success" });
    } catch (error) {
      console.error("Failed to update notification setting", error);
      setMessage({ text: "更新通知偏好失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handlePreferredDataSourceUpdate = async (dataSource: string) => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateSettings({ preferred_data_source: dataSource });
      setProfile(updated);
      setMessage({ text: `默认数据源已切换为 ${dataSource}。`, type: "success" });
    } catch (error: unknown) {
      console.error("Failed to update preferred data source", error);
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setMessage({ text: axiosErr.response?.data?.detail || "切换数据源失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotificationChannel = async () => {
    setSaving(true);
    try {
      await updateSettings({ feishu_webhook_url: feishuUrl });
      await loadProfile();
      setMessage({ text: "通知通道已保存。", type: "success" });
    } catch (error) {
      console.error("Failed to save notification channel", error);
      setMessage({ text: "保存通知通道失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTavilyCredential = async (withApiKey: boolean = true) => {
    setSaving(true);
    setMessage(null);
    setTavilyTestMessage(null);
    try {
      const tavilyPayload: { api_key?: string; is_enabled: boolean } = {
        is_enabled: tavilyEnabled,
      };
      if (withApiKey) {
        tavilyPayload.api_key = tavilyApiKey.trim();
      }
      await updateSettings({
        provider_credentials: {
          tavily: tavilyPayload,
        },
      });
      await loadProfile();
      setMessage({
        text: withApiKey
          ? (tavilyApiKey.trim() ? "Tavily 配置已保存。" : "Tavily API Key 已清空，开关状态已更新。")
          : "Tavily 开关状态已保存。",
        type: "success",
      });
    } catch (error) {
      console.error("Failed to save Tavily API key", error);
      setMessage({ text: "保存 Tavily 配置失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleTestTavily = async () => {
    setTestingTavily(true);
    setTavilyTestMessage(null);
    try {
      const result = await testTavilyConnection({
        api_key: tavilyApiKey.trim() || undefined,
      });
      setTavilyTestMessage({
        text: result.message,
        type: result.status === "success" ? "success" : "error",
      });
    } catch (error: unknown) {
      const errorMessage =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Tavily 测试失败。";
      setTavilyTestMessage({
        text: errorMessage || "Tavily 测试失败。",
        type: "error",
      });
    } finally {
      setTestingTavily(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMessage(null);
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordMessage({ text: "两次输入的新密码不一致。", type: "error" });
      return;
    }
    if (passwordForm.new_password.length < 6) {
      setPasswordMessage({ text: "新密码长度至少为 6 位。", type: "error" });
      return;
    }
    setPasswordLoading(true);
    try {
      await changePassword({ old_password: passwordForm.old_password, new_password: passwordForm.new_password });
      setPasswordForm({ old_password: "", new_password: "", confirm_password: "" });
      setPasswordMessage({ text: "密码更新成功。", type: "success" });
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setPasswordMessage({ text: axiosErr.response?.data?.detail || "更新密码失败。", type: "error" });
    } finally {
      setPasswordLoading(false);
    }
  };

  if (!authLoading && !token && !isAuthenticated) {
    return (
      <div className="p-8">
        <p className="text-sm text-slate-500">未登录，正在跳转到登录页...</p>
      </div>
    );
  }

  const renderGeneralSection = () => (
    <div className="space-y-8">
      <div className="space-y-3">
        <Label className="text-sm font-semibold">主题模式</Label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { key: "light", label: "浅色", icon: Sun },
            { key: "dark", label: "深色", icon: Moon },
            { key: "system", label: "跟随系统", icon: Sparkles },
          ].map((item) => {
            const Icon = item.icon;
            const active = mounted && currentTheme === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => handleThemeUpdate(item.key)}
                disabled={saving}
                className={`rounded-2xl border p-4 text-left transition ${
                  active
                    ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-950"
                    : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700"
                }`}
              >
                <Icon className="mb-4 h-5 w-5" />
                <div className="text-sm font-semibold">{item.label}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <div className="space-y-2">
          <Label htmlFor="timezone-select" className="text-sm font-semibold">时区</Label>
          <select
            id="timezone-select"
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
            value={profile?.timezone || authUser?.timezone || "Asia/Shanghai"}
            onChange={(e) => handleTimezoneUpdate(e.target.value)}
            disabled={saving}
          >
            <option value="Asia/Shanghai">北京 / 上海 (UTC+8)</option>
            <option value="Asia/Hong_Kong">香港 / 台北 (UTC+8)</option>
            <option value="Asia/Tokyo">东京 / 首尔 (UTC+9)</option>
            <option value="America/New_York">纽约 / 华盛顿</option>
            <option value="America/Los_Angeles">洛杉矶 / 旧金山</option>
            <option value="Europe/London">伦敦</option>
            <option value="UTC">UTC</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderAiSection = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">我的模型</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{availableModels.length} 个已配置的模型</p>
        </div>
        <Dialog
          open={isAddModelOpen}
          onOpenChange={(open) => {
            setIsAddModelOpen(open);
            if (!open) resetModelForm();
          }}
        >
          <DialogTrigger asChild>
            <Button variant="default" size="sm" className="gap-2" onClick={openAddModelDialog}>
              <Plus className="h-4 w-4" />
              添加模型
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <DialogHeader>
              <DialogTitle>{editingModelKey ? "编辑模型" : "添加新模型"}</DialogTitle>
              <DialogDescription>
                {editingModelKey ? "更新模型配置。API Key 留空时保留当前已保存的密钥。" : "添加一个新的 AI 模型到你的模型列表。"}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddModel} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="model-name">模型名称</Label>
                <Input id="model-name" placeholder="例如：Claude Sonnet 4" value={customModel.display_name} onChange={(e) => setCustomModel((prev) => ({ ...prev, display_name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model-id">模型名称标识</Label>
                <Input id="model-id" placeholder="例如：qwen3.5-plus / deepseek-r1 / gpt-4o-mini" value={customModel.model_id} onChange={(e) => setCustomModel((prev) => ({ ...prev, model_id: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model-base-url">Base URL</Label>
                <Input id="model-base-url" placeholder="例如：https://api.openai.com/v1" value={customModel.base_url} onChange={(e) => setCustomModel((prev) => ({ ...prev, base_url: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model-api-key">API Key</Label>
                <Input id="model-api-key" type="password" placeholder={editingModelKey ? "留空则保留当前密钥" : "输入可调用该模型的 API Key"} value={customModel.api_key} onChange={(e) => setCustomModel((prev) => ({ ...prev, api_key: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="provider-note">提供商备注</Label>
                <Input id="provider-note" placeholder="例如：OpenRouter / DeepSeek / 自建中转" value={customModel.provider_note} onChange={(e) => setCustomModel((prev) => ({ ...prev, provider_note: e.target.value }))} />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="space-y-0.5">
                  <Label htmlFor="is-default" className="text-sm font-medium">设为默认模型</Label>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    添加后自动将其设置为全站默认使用的 AI 模型
                  </p>
                </div>
                <Switch
                  checked={customModel.is_default}
                  onCheckedChange={(checked) => setCustomModel((prev) => ({ ...prev, is_default: checked }))}
                />
              </div>
              {modelTestMessage && (
                <div
                  className={`rounded-xl border px-4 py-3 text-sm ${
                    modelTestMessage.type === "success"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
                      : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
                  }`}
                >
                  {modelTestMessage.text}
                </div>
              )}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleTestModel} disabled={testingModel || addingModel}>
                  {testingModel ? "测试中..." : "测试连接"}
                </Button>
                <Button type="submit" disabled={addingModel}>{addingModel ? (editingModelKey ? "更新中..." : "添加中...") : (editingModelKey ? "保存修改" : "添加模型")}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-4">
        {availableModels.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
            还没有配置任何大模型。点击右上角“添加模型”开始。
          </div>
        ) : (
          <div className="space-y-4">
            {availableModels.map((model) => {
              const isDefault = profile?.preferred_ai_model === model.key;
              return (
                <div key={model.key} className="rounded-2xl border border-slate-200 px-5 py-5 dark:border-slate-800">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-base font-semibold text-slate-900 dark:text-slate-100">{model.display_name}</h4>
                        {isDefault && <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">默认</span>}
                        {model.is_builtin && <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-2.5 py-1 text-[11px] font-semibold text-sky-600 dark:text-sky-400">系统内置</span>}
                        <span className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 dark:border-slate-700 dark:text-slate-400">
                          {model.is_active ? "已启用" : "已停用"}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                        {(model.provider_note || "未填写提供商备注")} · {model.model_id}
                      </p>
                    </div>
                    <Switch checked={Boolean(model.is_active)} disabled />
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-600 dark:text-slate-300">
                    <div className="min-w-0">
                      <span className="mr-2 text-slate-500 dark:text-slate-400">API 密钥:</span>
                      <span className="font-mono font-medium text-slate-900 dark:text-slate-100">
                        {model.masked_api_key || (model.has_api_key ? "已保存" : "未保存")}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <span className="mr-2 text-slate-500 dark:text-slate-400">API 地址:</span>
                      <span className="font-mono font-medium text-slate-900 dark:text-slate-100">
                        {maskText(normalizeBaseUrl(model.base_url), 56)}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-end gap-2">
                    {!isDefault && <Button variant="outline" size="sm" onClick={() => handleSetDefaultModel(model.key)} disabled={saving || deletingModelKey === model.key}>设为默认</Button>}
                    {!model.is_builtin && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => openEditModelDialog(model)} disabled={saving || deletingModelKey === model.key}>
                          <Pencil className="mr-1.5 h-4 w-4" />
                          编辑
                        </Button>
                        <Button variant="ghost" size="sm" className="text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300" onClick={() => handleDeleteModel(model.key)} disabled={deletingModelKey !== null || saving}>
                          {deletingModelKey === model.key ? "删除中..." : "删除"}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );

  const renderNotificationsSection = () => (
    <div className="space-y-8">
      <div className="space-y-2">
        <Label htmlFor="feishu-webhook" className="text-sm font-semibold">飞书机器人 Webhook</Label>
        <Input id="feishu-webhook" type="text" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." value={feishuUrl} onChange={(e) => setFeishuUrl(e.target.value)} />
        <Button variant="outline" onClick={handleSaveNotificationChannel} disabled={saving}>
          <Save className="mr-2 h-4 w-4" />
          保存通知通道
        </Button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-2xl border border-slate-900/5 bg-slate-50 p-6 dark:border-white/5 dark:bg-white/5">
          <div>
            <div className="text-base font-semibold text-slate-900 dark:text-slate-100">全局通知开关</div>
            <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">开启或关闭系统所有自动推送（如价格预警、每日报告等）。</div>
          </div>
          <Switch
            checked={Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true)}
            disabled={saving}
            onCheckedChange={(checked) => handleToggleSwitch("notifications_enabled", checked)}
            className="data-[state=checked]:bg-emerald-500"
          />
        </div>
      </div>

      <div className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <div className="space-y-3">
          {[
            { key: "enable_price_alerts" as const, title: "价格 / 风险预警", description: "触达止盈止损或指标异常时推送。" },
            { key: "enable_hourly_summary" as const, title: "持仓整点摘要", description: "每小时对持仓标的做新闻与行情总结。" },
            { key: "enable_daily_report" as const, title: "每日持仓报告", description: "北京时间 09:00 / 22:00 生成深度持仓体检。" },
            { key: "enable_macro_alerts" as const, title: "全球宏观提醒", description: "推送影响全球市场的大事件与风险。" },
          ].map((item) => (
            <div key={item.key} className="flex items-center justify-between border-b border-slate-200 py-4 last:border-b-0 dark:border-slate-800">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.description}</div>
              </div>
              <Switch
                checked={Boolean(profile?.[item.key] ?? authUser?.[item.key])}
                disabled={saving || !Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true)}
                onCheckedChange={(checked) => handleToggleSwitch(item.key, checked)}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderSecuritySection = () => (
    <div className="space-y-8">
      <form onSubmit={handleChangePassword} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="old-password">当前密码</Label>
          <Input id="old-password" type="password" value={passwordForm.old_password} onChange={(e) => setPasswordForm((prev) => ({ ...prev, old_password: e.target.value }))} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="new-password">新密码</Label>
            <Input id="new-password" type="password" value={passwordForm.new_password} onChange={(e) => setPasswordForm((prev) => ({ ...prev, new_password: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">确认新密码</Label>
            <Input id="confirm-password" type="password" value={passwordForm.confirm_password} onChange={(e) => setPasswordForm((prev) => ({ ...prev, confirm_password: e.target.value }))} />
          </div>
        </div>
        <div className="border-t border-slate-200 pt-4 dark:border-slate-800">
          {passwordMessage && (
            <div
              className={`mb-4 rounded-xl border px-4 py-3 text-sm ${
                passwordMessage.type === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
                  : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
              }`}
            >
              {passwordMessage.text}
            </div>
          )}
          <Button type="submit" disabled={passwordLoading}>{passwordLoading ? "更新中..." : "更新密码"}</Button>
        </div>
      </form>
    </div>
  );

  const renderDataSection = () => (
    <div className="space-y-8">
      <div className="rounded-2xl border border-slate-200 px-5 py-5 dark:border-slate-800">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">默认行情数据源</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              选择账户默认使用的数据源。不同服务器环境可看到不同的可用源状态。
            </p>
          </div>
          <span className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-500 dark:border-slate-700 dark:text-slate-400">
            当前: {selectedDataSource?.label || profile?.preferred_data_source || "AKSHARE"}
          </span>
        </div>
        <div className="mt-4 space-y-3">
          {availableDataSources.map((source) => {
            const active = (profile?.preferred_data_source || "AKSHARE") === source.key;
            return (
              <div
                key={source.key}
                className={`rounded-2xl border px-4 py-4 transition ${
                  active
                    ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-950"
                    : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-semibold">{source.label}</div>
                      {source.is_default && (
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${active ? "border-white/30 text-white/80 dark:border-slate-500 dark:text-slate-700" : "border-sky-500/20 bg-sky-500/10 text-sky-600 dark:text-sky-400"}`}>
                          系统默认
                        </span>
                      )}
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${source.is_available ? (active ? "border-white/30 text-white/80 dark:border-slate-500 dark:text-slate-700" : "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400") : "border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400"}`}>
                        {source.is_available ? "可用" : "当前不可用"}
                      </span>
                    </div>
                    <p className={`mt-2 text-sm ${active ? "text-white/80 dark:text-slate-700" : "text-slate-500 dark:text-slate-400"}`}>
                      {source.description}
                    </p>
                  </div>
                  <Button
                    variant={active ? "secondary" : "outline"}
                    size="sm"
                    disabled={saving || !source.is_available || active}
                    onClick={() => handlePreferredDataSourceUpdate(source.key)}
                  >
                    {active ? "当前使用中" : "设为默认"}
                  </Button>
                </div>
              </div>
            );
          })}
          {availableDataSources.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              暂未获取到可选数据源。
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 px-5 py-5 dark:border-slate-800">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Tavily 搜索 API</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              用于全球宏观与新闻检索。支持独立开关、连接测试与密钥更新。
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                hasSavedTavilyKey
                  ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400"
              }`}
            >
              {hasSavedTavilyKey ? "已保存密钥" : "未保存密钥"}
            </span>
            <div className="flex items-center gap-2">
              <Label htmlFor="tavily-enabled" className="text-xs text-slate-500 dark:text-slate-400">启用</Label>
              <Switch
                id="tavily-enabled"
                checked={tavilyEnabled}
                disabled={saving}
                onCheckedChange={(checked) => setTavilyEnabled(checked)}
              />
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-3 md:flex-row">
          <Input
            type="password"
            placeholder={hasSavedTavilyKey ? "已保存，输入新值可覆盖" : "输入 Tavily API Key"}
            value={tavilyApiKey}
            onChange={(e) => setTavilyApiKey(e.target.value)}
          />
          <Button
            variant="outline"
            onClick={() => handleSaveTavilyCredential(true)}
            disabled={saving}
            className="md:min-w-[132px]"
          >
            <Save className="mr-2 h-4 w-4" />
            保存配置
          </Button>
          <Button
            variant="outline"
            onClick={handleTestTavily}
            disabled={testingTavily}
            className="md:min-w-[132px]"
          >
            {testingTavily ? "测试中..." : "测试连接"}
          </Button>
        </div>
        {tavilyTestMessage && (
          <div
            className={`mt-3 rounded-xl border px-4 py-3 text-sm ${
              tavilyTestMessage.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
                : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
            }`}
          >
            {tavilyTestMessage.text}
          </div>
        )}
        <div className="mt-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleSaveTavilyCredential(false)}
            disabled={saving}
          >
            仅保存开关状态
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="border-r border-slate-200 pr-4 dark:border-slate-800">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">我的模型</div>
          <div className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100">{availableModels.length}</div>
        </div>
        <div className="border-r border-slate-200 px-4 dark:border-slate-800">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">当前默认模型</div>
          <div className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{selectedModel?.display_name || profile?.preferred_ai_model || "未设置"}</div>
        </div>
        <div className="pl-4">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">当前主题</div>
          <div className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{profile?.theme || authUser?.theme || "未设置"}</div>
        </div>
      </div>

      <div className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => { void loadProfile(); void loadModels(); void loadDataSources(); }}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            重新同步配置
          </Button>
          <Button variant="outline" onClick={() => { void loadDataSources(); }}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            刷新数据源状态
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              resetModelForm();
              setMessage({ text: "添加模型弹窗的临时输入已清空。", type: "success" });
            }}
          >
            清空未保存输入
          </Button>
        </div>
      </div>
    </div>
  );

  const activeSectionConfig = SECTION_ITEMS.find((item) => item.id === activeSection)!;

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 dark:bg-slate-950 md:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="icon" className="rounded-full">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">设置</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {profileLoading ? "正在同步最新设置..." : "沿用当前主题体系，重组为更清晰的工作区式设置中心。"}
            </p>
          </div>
        </div>

        {message && (
          <div className={`mb-6 rounded-2xl border px-4 py-3 text-sm ${
            message.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
              : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
          }`}>
            {message.text}
          </div>
        )}

        <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="grid min-h-[760px] lg:grid-cols-[280px_1fr]">
            <aside className="border-b border-slate-200 bg-slate-50/80 p-5 dark:border-slate-800 dark:bg-slate-950/80 lg:border-b-0 lg:border-r">
              <div className="mb-6">
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">设置</h2>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">管理您的账户、AI 模型与自动化偏好。</p>
              </div>

              <nav className="space-y-2">
                {SECTION_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const active = activeSection === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setActiveSection(item.id)}
                      className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left transition ${
                        active ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950" : "hover:bg-slate-100 dark:hover:bg-slate-900"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`h-4 w-4 ${active ? "" : "text-slate-500"}`} />
                        <div>
                          <div className="text-sm font-semibold">{item.label}</div>
                          <div className={`text-xs ${active ? "text-slate-300 dark:text-slate-600" : "text-slate-500 dark:text-slate-400"}`}>{item.description}</div>
                        </div>
                      </div>
                      <ChevronRight className={`h-4 w-4 ${active ? "opacity-100" : "opacity-40"}`} />
                    </button>
                  );
                })}
              </nav>
            </aside>

            <main className="p-6 lg:p-8">
              <div className="mb-8">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  <activeSectionConfig.icon className="h-4 w-4" />
                  {activeSectionConfig.label}
                </div>
                <h3 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                  {activeSection === "general" && "通用设置"}
                  {activeSection === "ai" && "AI 配置"}
                  {activeSection === "notifications" && "通知设置"}
                  {activeSection === "security" && "安全设置"}
                  {activeSection === "data" && "数据管理"}
                </h3>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{activeSectionConfig.description}</p>
              </div>

              {activeSection === "general" && renderGeneralSection()}
              {activeSection === "ai" && renderAiSection()}
              {activeSection === "notifications" && renderNotificationsSection()}
              {activeSection === "security" && renderSecuritySection()}
              {activeSection === "data" && renderDataSection()}
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
