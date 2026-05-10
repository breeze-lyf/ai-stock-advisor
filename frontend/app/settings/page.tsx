"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import {
  BellRing,
  ArrowLeft,
  Bell,
  Bot,
  ChevronRight,
  HardDrive,
  Moon,
  Pencil,
  Plus,
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { NotificationSettingsSection } from "@/features/user/components/NotificationSettingsSection";
import {
  changePassword,
  createAIModel,
  deleteAIModel,
  getDataSourceSettings,
  getProfile,
  listAIModels,
  testAIConnection,
  testDataSource,
  testTavilyConnection,
  testFeishuWebhook,
  getNotificationRoutingSettings,
  getBrowserPushConfig,
  getBrowserPushSubscriptions,
  testNotificationRouting,
  subscribeBrowserPush,
  unsubscribeBrowserPush,
  unsubscribeBrowserPushByEndpoint,
  updateDataSourceSettings,
  updateNotificationRoutingSettings,
  updateSettings,
  type AIModelConfigItem,
  type CreateAIModelConfigInput,
  type DataSourceSettings,
  type DataSourceSettingsUpdate,
  type MarketDataSourceConfig,
  type MarketDataSourceOption,
  type BrowserPushConfig,
  type BrowserPushSubscriptionItem,
  type NotificationRoutingSettings,
} from "@/features/user/api";
import type { UserProfile } from "@/types";
import { getCurrentBrowserEndpoint, hasCurrentBrowserSubscription, subscribeCurrentBrowser, unsubscribeCurrentBrowser } from "@/lib/web-push";

type SettingsSection = "general" | "ai" | "notifications" | "security" | "data";

const SECTION_ITEMS: Array<{ id: SettingsSection; label: string; description: string; icon: typeof Settings2 }> = [
  { id: "general", label: "通用设置", description: "主题与时区", icon: Settings2 },
  { id: "ai", label: "AI 配置", description: "默认模型与我的模型", icon: Bot },
  { id: "data", label: "数据管理", description: "配置状态与同步", icon: HardDrive },
  { id: "notifications", label: "通知", description: "飞书与推送偏好", icon: Bell },
  { id: "security", label: "安全", description: "密码管理", icon: Shield },
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
  const [advancedNotificationsOpen, setAdvancedNotificationsOpen] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(authUser);
  const [profileLoading, setProfileLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const [availableModels, setAvailableModels] = useState<AIModelConfigItem[]>([]);
  const [availableDataSources, setAvailableDataSources] = useState<MarketDataSourceOption[]>([]);
  const [dataSourceConfig, setDataSourceConfig] = useState<DataSourceSettings | null>(null);
  const [dataSourceLoading, setDataSourceLoading] = useState(false);
  const [dataSourceMessage, setDataSourceMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [savingDataSource, setSavingDataSource] = useState(false);
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
  const [testingFeishu, setTestingFeishu] = useState(false);
  const [feishuTestMessage, setFeishuTestMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [notificationRouting, setNotificationRouting] = useState<NotificationRoutingSettings | null>(null);
  const [browserPushConfig, setBrowserPushConfig] = useState<BrowserPushConfig | null>(null);
  const [browserPushSubscriptions, setBrowserPushSubscriptions] = useState<BrowserPushSubscriptionItem[]>([]);
  const [currentBrowserSubscribed, setCurrentBrowserSubscribed] = useState(false);
  const [browserPushLoading, setBrowserPushLoading] = useState(false);
  const [routingLoading, setRoutingLoading] = useState(false);
  const [routingMessage, setRoutingMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [testingNotificationPriority, setTestingNotificationPriority] = useState<"P0" | "P1" | "P2" | "P3" | null>(null);
  const [testingDataSource, setTestingDataSource] = useState<string | null>(null);
  const [dataSourceTestMessage, setDataSourceTestMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [useWorkerProxy, setUseWorkerProxy] = useState(false);
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
  }, [authUser]);

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
    } catch (error) {
      console.error("Failed to load profile", error);
    } finally {
      setProfileLoading(false);
    }
  }, []);

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
    setDataSourceLoading(true);
    try {
      const data = await getDataSourceSettings();
      setDataSourceConfig(data);
      setAvailableDataSources(data.available_sources);
    } catch (error) {
      console.error("Failed to load data source settings", error);
      setAvailableDataSources([]);
    } finally {
      setDataSourceLoading(false);
    }
  }, []);

  const loadNotificationRouting = useCallback(async () => {
    setRoutingLoading(true);
    try {
      const settings = await getNotificationRoutingSettings();
      setNotificationRouting(settings);
    } catch (error) {
      console.error("Failed to load notification routing settings", error);
      setNotificationRouting(null);
    } finally {
      setRoutingLoading(false);
    }
  }, []);

  const loadBrowserPushState = useCallback(async () => {
    setBrowserPushLoading(true);
    try {
      const [config, subscriptions, subscribed] = await Promise.all([
        getBrowserPushConfig(),
        getBrowserPushSubscriptions(),
        hasCurrentBrowserSubscription().catch(() => false),
      ]);
      setBrowserPushConfig(config);
      setBrowserPushSubscriptions(subscriptions);
      setCurrentBrowserSubscribed(subscribed);
    } catch (error) {
      console.error("Failed to load browser push state", error);
      setBrowserPushConfig(null);
      setBrowserPushSubscriptions([]);
      setCurrentBrowserSubscribed(false);
    } finally {
      setBrowserPushLoading(false);
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
    void loadNotificationRouting();
    void loadBrowserPushState();
  }, [authLoading, isAuthenticated, loadBrowserPushState, loadDataSources, loadModels, loadNotificationRouting, loadProfile, token]);

  const selectedModel = useMemo(
    () => availableModels.find((model) => model.key === (profile?.preferred_ai_model || "")) || null,
    [availableModels, profile?.preferred_ai_model],
  );

  const notificationsEnabled = Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true);
  const coreEnabledCount = [
    profile?.enable_price_alerts ?? authUser?.enable_price_alerts,
    profile?.enable_macro_alerts ?? authUser?.enable_macro_alerts,
    profile?.enable_strategy_change_alerts ?? authUser?.enable_strategy_change_alerts,
    profile?.enable_daily_report ?? authUser?.enable_daily_report,
  ].filter(Boolean).length;
  const hasAnyPrimaryChannel = Boolean(notificationRouting?.feishu_enabled || notificationRouting?.email_enabled || notificationRouting?.browser_push_enabled);
  const notificationReadiness = !notificationsEnabled
    ? "off"
    : !hasAnyPrimaryChannel && !feishuUrl.trim()
      ? "channel_missing"
      : coreEnabledCount <= 1
        ? "minimal"
        : coreEnabledCount <= 3
          ? "balanced"
          : "complete";

  const handleSetDefaultModel = async (modelKey: string) => {
    setSaving(true);
    setMessage(null);
    try {
      await updateSettings({ preferred_ai_model: modelKey });
      await Promise.all([loadProfile(), loadModels()]);
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
      model_id: customModel.display_name.trim(),
      api_key: customModel.api_key.trim() || undefined,
      base_url: normalizeBaseUrl(customModel.base_url),
      is_default: customModel.is_default,
    };

    if (!payload.display_name || !payload.base_url) {
      setMessage({ text: "请填写模型名称和 Base URL。", type: "error" });
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

      // Refresh all data from server
      await Promise.all([loadModels(), loadProfile()]);

      // UI reset
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
          : (payload.is_default ? `模型 ${savedModel.display_name} 已添加并设为默认。` : `模型 ${savedModel.display_name} 已添加。`),
        type: "success",
      });
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
      model_id: customModel.display_name.trim(),
      api_key: customModel.api_key.trim() || undefined,
      base_url: normalizeBaseUrl(customModel.base_url),
    };

    if (!payload.model_id || !payload.base_url) {
      setModelTestMessage({ text: "测试前请先填写模型名称和 Base URL。", type: "error" });
      return;
    }
    if (!payload.api_key && !editingModelKey) {
      setModelTestMessage({ text: "测试前请先填写模型名称、API Key 和 Base URL。", type: "error" });
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
      display_name: model.model_id,
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
      await Promise.all([loadModels(), loadProfile()]);
      setMessage({ text: response.message || "模型已删除。", type: "success" });
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setMessage({ text: axiosErr.response?.data?.detail || "删除模型失败。", type: "error" });
    } finally {
      setDeletingModelKey(null);
    }
  };

  const handleThemeUpdate = async (theme: string) => {
    if (saving || currentTheme === theme) return;
    setSaving(true);
    setMessage(null);
    setTheme(theme);
    try {
      const updatedProfile = await updateSettings({ theme });
      setProfile(updatedProfile);
      setMessage({ text: "外观主题已更新。", type: "success" });
    } catch (error) {
      console.error("Failed to update theme", error);
      if (profile?.theme) {
        setTheme(profile.theme);
      } else if (authUser?.theme) {
        setTheme(authUser.theme);
      }
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

  const applyNotificationPreset = async (preset: "light" | "balanced" | "active") => {
    setSaving(true);
    setRoutingMessage(null);
    setMessage(null);

    const contentPatch: Partial<UserProfile> =
      preset === "light"
        ? {
            notifications_enabled: true,
            enable_price_alerts: true,
            enable_macro_alerts: true,
            enable_strategy_change_alerts: true,
            enable_daily_report: false,
            enable_indicator_alerts: false,
            enable_hourly_summary: false,
          }
        : preset === "balanced"
          ? {
              notifications_enabled: true,
              enable_price_alerts: true,
              enable_macro_alerts: true,
              enable_strategy_change_alerts: true,
              enable_daily_report: true,
              enable_indicator_alerts: false,
              enable_hourly_summary: false,
            }
          : {
              notifications_enabled: true,
              enable_price_alerts: true,
              enable_macro_alerts: true,
              enable_strategy_change_alerts: true,
              enable_daily_report: true,
              enable_indicator_alerts: true,
              enable_hourly_summary: true,
            };

    const routingPatch: Partial<NotificationRoutingSettings> =
      preset === "light"
        ? {
            quiet_mode_enabled: true,
            quiet_mode_start: notificationRouting?.quiet_mode_start || "22:30",
            quiet_mode_end: notificationRouting?.quiet_mode_end || "07:30",
            p1_daily_limit: 8,
            p2_daily_limit: 3,
            p3_daily_limit: 2,
          }
        : preset === "balanced"
          ? {
              quiet_mode_enabled: true,
              quiet_mode_start: notificationRouting?.quiet_mode_start || "22:30",
              quiet_mode_end: notificationRouting?.quiet_mode_end || "07:30",
              p1_daily_limit: 12,
              p2_daily_limit: 5,
              p3_daily_limit: 4,
            }
          : {
              quiet_mode_enabled: false,
              p1_daily_limit: 20,
              p2_daily_limit: 8,
              p3_daily_limit: 8,
            };

    try {
      const [updatedProfile, updatedRouting] = await Promise.all([
        updateSettings(contentPatch),
        updateNotificationRoutingSettings(routingPatch),
      ]);
      setProfile(updatedProfile);
      setNotificationRouting(updatedRouting);
      setMessage({
        text:
          preset === "light"
            ? "已切换到轻提醒模式。"
            : preset === "balanced"
              ? "已切换到平衡模式。"
              : "已切换到高敏感模式。",
        type: "success",
      });
    } catch (error) {
      console.error("Failed to apply notification preset", error);
      setMessage({ text: "应用通知预设失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleDataSourceConfigUpdate = async (market: keyof MarketDataSourceConfig, value: string) => {
    setSavingDataSource(true);
    setDataSourceMessage(null);
    try {
      const payload: DataSourceSettingsUpdate = { [market]: value };
      const result = await updateDataSourceSettings(payload);
      if (result.status === "success") {
        setDataSourceMessage({ text: "数据源配置已更新。", type: "success" });
        // Reload to get updated config
        await loadProfile();
        await loadDataSources();
      }
    } catch (error: unknown) {
      console.error("Failed to update data source config", error);
      const axiosErr = error as { response?: { data?: { detail?: string } } };
      setDataSourceMessage({ text: axiosErr.response?.data?.detail || "更新数据源配置失败。", type: "error" });
    } finally {
      setSavingDataSource(false);
    }
  };

  const handleTestDataSource = async (market: keyof MarketDataSourceConfig) => {
    setTestingDataSource(market);
    setDataSourceTestMessage(null);
    try {
      const sourceMap: Record<keyof MarketDataSourceConfig, string> = {
        a_share: "AKSHARE",
        hk_share: "AKSHARE",
        us_share: "YFINANCE",
      };
      const result = await testDataSource(sourceMap[market]);
      setDataSourceTestMessage({
        text: result.message || `${market === "a_share" ? "A 股" : market === "hk_share" ? "港股" : "美股"}数据源连接正常。`,
        type: "success"
      });
    } catch (error: unknown) {
      const axiosErr = error as { response?: { data?: { message?: string; detail?: string } } };
      const detail = axiosErr.response?.data?.message || axiosErr.response?.data?.detail;
      setDataSourceTestMessage({
        text: detail || "无法连接到数据源",
        type: "error"
      });
    } finally {
      setTestingDataSource(null);
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

  const handleRoutingSettingUpdate = async (patch: Partial<NotificationRoutingSettings>, successText = "通知路由已更新。") => {
    setSaving(true);
    setRoutingMessage(null);
    try {
      const next = await updateNotificationRoutingSettings(patch);
      setNotificationRouting(next);
      setRoutingMessage({ text: successText, type: "success" });
    } catch (error) {
      console.error("Failed to update notification routing", error);
      setRoutingMessage({ text: "更新通知路由失败。", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleTestNotificationRouting = async (priority: "P0" | "P1" | "P2" | "P3") => {
    setTestingNotificationPriority(priority);
    setRoutingMessage(null);
    try {
      const response = await testNotificationRouting(priority);
      const sent = response.result.sent_channels.length ? `已发送: ${response.result.sent_channels.join(", ")}` : "未发送到任何渠道";
      const blocked = response.result.blocked_reason ? `；阻塞原因: ${response.result.blocked_reason}` : "";
      const skipped = response.result.skipped_channels.length ? `；跳过: ${response.result.skipped_channels.join(", ")}` : "";
      setRoutingMessage({
        text: `${priority} 测试通知已执行，${sent}${blocked}${skipped}`,
        type: response.result.sent_channels.length > 0 ? "success" : "error",
      });
    } catch (error) {
      console.error("Failed to test notification routing", error);
      setRoutingMessage({ text: "测试通知失败。", type: "error" });
    } finally {
      setTestingNotificationPriority(null);
    }
  };

  const handleSubscribeCurrentBrowser = async () => {
    setSaving(true);
    setRoutingMessage(null);
    try {
      if (!browserPushConfig?.web_push_enabled || !browserPushConfig.vapid_public_key) {
        throw new Error("服务端未启用 Web Push 或缺少 VAPID 公钥");
      }

      const payload = await subscribeCurrentBrowser(browserPushConfig.vapid_public_key);
      const browserName =
        typeof navigator !== "undefined"
          ? navigator.userAgent.includes("Chrome")
            ? "Chrome"
            : navigator.userAgent.includes("Safari")
              ? "Safari"
              : navigator.userAgent.includes("Firefox")
                ? "Firefox"
                : "Browser"
          : "Browser";

      await subscribeBrowserPush({
        ...payload,
        browser: browserName,
        device_name: `${browserName} on ${profile?.timezone || "current device"}`,
      });
      await handleRoutingSettingUpdate({ browser_push_enabled: true }, "当前浏览器已完成推送订阅。");
      await loadBrowserPushState();
    } catch (error) {
      console.error("Failed to subscribe current browser", error);
      setRoutingMessage({
        text: error instanceof Error ? error.message : "当前浏览器订阅失败。",
        type: "error",
      });
      setSaving(false);
    }
  };

  const handleUnsubscribeCurrentBrowser = async () => {
    setSaving(true);
    setRoutingMessage(null);
    try {
      const endpoint = await getCurrentBrowserEndpoint();
      if (endpoint) {
        await unsubscribeBrowserPushByEndpoint(endpoint).catch(() => null);
      }
      await unsubscribeCurrentBrowser();
      await loadBrowserPushState();
      if (browserPushSubscriptions.length <= 1) {
        await handleRoutingSettingUpdate({ browser_push_enabled: false }, "当前浏览器的推送订阅已移除。");
        return;
      }
      setRoutingMessage({ text: "当前浏览器的推送订阅已移除。", type: "success" });
      setSaving(false);
    } catch (error) {
      console.error("Failed to unsubscribe current browser", error);
      setRoutingMessage({ text: "移除当前浏览器推送订阅失败。", type: "error" });
      setSaving(false);
    }
  };

  const handleRemoveBrowserSubscription = async (subscriptionId: string) => {
    setSaving(true);
    setRoutingMessage(null);
    try {
      await unsubscribeBrowserPush(subscriptionId);
      await loadBrowserPushState();
      if (browserPushSubscriptions.length <= 1) {
        await handleRoutingSettingUpdate({ browser_push_enabled: false }, "浏览器推送设备已移除。");
        return;
      }
      setRoutingMessage({ text: "浏览器推送设备已移除。", type: "success" });
      setSaving(false);
    } catch (error) {
      console.error("Failed to remove browser push subscription", error);
      setRoutingMessage({ text: "移除浏览器推送设备失败。", type: "error" });
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

  const handleTestFeishu = async () => {
    setTestingFeishu(true);
    setFeishuTestMessage(null);
    try {
      const result = await testFeishuWebhook({
        webhook_url: feishuUrl.trim() || undefined,
      });
      setFeishuTestMessage({
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
          : "飞书 Webhook 测试失败。";
      setFeishuTestMessage({
        text: errorMessage || "飞书 Webhook 测试失败。",
        type: "error",
      });
    } finally {
      setTestingFeishu(false);
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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={async () => {
              await Promise.all([loadModels(), loadProfile(), loadDataSources()]);
              setMessage({ text: "数据已刷新。", type: "success" });
            }}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新
          </Button>
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
                <Input id="model-name" placeholder="例如：Pro/deepseek-ai/DeepSeek-V3 / gpt-4o-mini" value={customModel.display_name} onChange={(e) => setCustomModel((prev) => ({ ...prev, display_name: e.target.value }))} />
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
      <div className="rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-emerald-50/60 p-6 dark:border-slate-800 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950/20">
        <div className="max-w-2xl">
          <div className="text-lg font-semibold text-slate-900 dark:text-slate-100">通知应该帮你决策，不该制造噪音</div>
          <div className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            默认只建议保留最关键的 4 类提醒：价格预警、策略变更、宏观重大事件、每日复盘。
            更细的技术指标、整点摘要和路由规则都收在下方高级设置里，需要时再展开。
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="feishu-webhook" className="text-sm font-semibold">飞书机器人 Webhook</Label>
        <Input id="feishu-webhook" type="text" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." value={feishuUrl} onChange={(e) => setFeishuUrl(e.target.value)} />
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSaveNotificationChannel} disabled={saving}>
            <Save className="mr-2 h-4 w-4" />
            保存通知通道
          </Button>
          <Button
            variant="outline"
            onClick={handleTestFeishu}
            disabled={testingFeishu}
            className="md:min-w-33"
          >
            {testingFeishu ? "测试中..." : "测试连接"}
          </Button>
        </div>
        {feishuTestMessage && (
          <div
            className={`mt-3 rounded-xl border px-4 py-3 text-sm ${
              feishuTestMessage.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
                : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
            }`}
          >
            {feishuTestMessage.text}
          </div>
        )}
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

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">快速开始</div>
          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">不想自己逐项配置时，可以直接套用一套推荐模式。</div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" disabled={saving} onClick={() => void applyNotificationPreset("light")}>轻提醒</Button>
            <Button variant="outline" disabled={saving} onClick={() => void applyNotificationPreset("balanced")}>平衡模式</Button>
            <Button variant="outline" disabled={saving} onClick={() => void applyNotificationPreset("active")}>高敏感模式</Button>
          </div>
          <div className="mt-4 text-xs leading-6 text-slate-500 dark:text-slate-400">
            轻提醒：只保留最关键事件。
            平衡模式：适合大多数人。
            高敏感模式：适合高频关注市场的用户。
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">当前状态</div>
          <div className="mt-3 space-y-3">
            <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-900/60">
              <div className="font-medium text-slate-900 dark:text-slate-100">
                {notificationReadiness === "off" && "通知总开关已关闭"}
                {notificationReadiness === "channel_missing" && "还没真正连上通知渠道"}
                {notificationReadiness === "minimal" && "通知比较克制"}
                {notificationReadiness === "balanced" && "通知配置比较均衡"}
                {notificationReadiness === "complete" && "通知配置已经比较完整"}
              </div>
              <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {notificationReadiness === "off" && "系统不会主动推送任何提醒。"}
                {notificationReadiness === "channel_missing" && "建议至少配置飞书或启用浏览器推送，否则很多提醒发不出去。"}
                {notificationReadiness === "minimal" && "适合不想被频繁打扰，但仍希望收到关键风险提醒。"}
                {notificationReadiness === "balanced" && "已经覆盖大部分关键场景，适合作为默认配置。"}
                {notificationReadiness === "complete" && "覆盖面最全，但也更容易在行情波动时收到较多提醒。"}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">核心通知已开启</div>
                <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{coreEnabledCount}/4</div>
              </div>
              <div className="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">可用主渠道</div>
                <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">{hasAnyPrimaryChannel || feishuUrl.trim() ? "已连接" : "未连接"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <div className="mb-4">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">核心通知</div>
          <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">这 4 类最值得默认开启，既能覆盖风险，也不容易把人吵烦。</div>
        </div>

        <div className="space-y-3">
          {[
            { key: "enable_price_alerts" as const, title: "价格预警", description: "到达止盈止损位时第一时间提醒。" },
            { key: "enable_macro_alerts" as const, title: "全球宏观提醒", description: "推送影响全球市场的大事件与风险。" },
            { key: "enable_strategy_change_alerts" as const, title: "策略变更", description: "盘后复盘发现操作建议显著变化时提醒。" },
            { key: "enable_daily_report" as const, title: "每日复盘报告", description: "每天给你一份更完整的持仓体检。" },
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

      <div className="border-t border-slate-200 pt-6 dark:border-slate-800">
        <div className="space-y-4 rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left"
            onClick={() => setAdvancedNotificationsOpen((prev) => !prev)}
          >
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">高级通知设置</div>
              <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                包括技术指标提醒、整点摘要、浏览器设备、静默时段和发送规则。默认折叠，避免设置过载。
              </div>
            </div>
            <ChevronRight
              className={`h-4 w-4 text-slate-500 transition-transform ${advancedNotificationsOpen ? "rotate-90" : ""}`}
            />
          </button>

          {advancedNotificationsOpen && (
            <div className="space-y-8 border-t border-slate-200 pt-5 dark:border-slate-800">
              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">补充型通知</div>
                <div className="space-y-3">
                  {[
                    { key: "enable_indicator_alerts" as const, title: "技术指标提醒", description: "RSI 等指标进入极端区间时提醒。适合盯盘型用户。" },
                    { key: "enable_hourly_summary" as const, title: "整点摘要", description: "每小时推送一次新闻与行情总结。信息量大，更适合重度用户。" },
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

              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">通知渠道</div>
                {routingMessage && (
                  <div
                    className={`mb-4 rounded-xl border px-4 py-3 text-sm ${
                      routingMessage.type === "success"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300"
                        : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300"
                    }`}
                  >
                    {routingMessage.text}
                  </div>
                )}

                <div className="space-y-3">
                  {[
                    { key: "feishu_enabled" as const, title: "飞书", description: "最适合接收关键提醒，及时、稳定、到达率高。" },
                    { key: "email_enabled" as const, title: "邮件", description: "更适合日报、复盘和偏长内容。" },
                    { key: "browser_push_enabled" as const, title: "浏览器弹窗", description: "适合办公场景，需要先完成当前浏览器订阅。" },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between border-b border-slate-200 py-4 last:border-b-0 dark:border-slate-800">
                      <div>
                        <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.description}</div>
                      </div>
                      <Switch
                        checked={Boolean(notificationRouting?.[item.key])}
                        disabled={saving || routingLoading}
                        onCheckedChange={(checked) => void handleRoutingSettingUpdate({ [item.key]: checked })}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">当前浏览器订阅</div>
                <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <BellRing className="h-4 w-4 text-slate-500" />
                        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                          {browserPushConfig?.web_push_enabled ? "浏览器推送服务已启用" : "浏览器推送服务未启用"}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {browserPushConfig?.web_push_enabled
                          ? currentBrowserSubscribed
                            ? "当前浏览器已经拿到订阅凭证，可以接收桌面提醒。"
                            : "当前浏览器还没有完成订阅，点击右侧按钮即可注册。"
                          : "当前环境还没有配置 Web Push 所需密钥，所以这里暂时不能用。"}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        disabled={saving || browserPushLoading || !browserPushConfig?.web_push_enabled}
                        onClick={() => void handleSubscribeCurrentBrowser()}
                      >
                        {saving && !currentBrowserSubscribed ? "连接中..." : "连接当前浏览器"}
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={saving || browserPushLoading || (!currentBrowserSubscribed && browserPushSubscriptions.length === 0)}
                        onClick={() => void handleUnsubscribeCurrentBrowser()}
                      >
                        断开当前浏览器
                      </Button>
                    </div>
                  </div>

                  <div className="mt-5 border-t border-slate-200 pt-4 dark:border-slate-800">
                    <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">已注册设备</div>
                    {browserPushSubscriptions.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-slate-300 px-4 py-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                        还没有浏览器设备完成推送注册。
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {browserPushSubscriptions.map((subscription) => (
                          <div key={subscription.id} className="rounded-xl border border-slate-200 px-4 py-4 dark:border-slate-800">
                            <div className="flex items-center justify-between gap-4">
                              <div>
                                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                                  {subscription.device_name || "未命名设备"}
                                </div>
                                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                  {subscription.browser || "未知浏览器"} · 创建于 {new Date(subscription.created_at).toLocaleString("zh-CN")}
                                </div>
                                {subscription.last_used_at && (
                                  <div className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                                    最近使用 {new Date(subscription.last_used_at).toLocaleString("zh-CN")}
                                  </div>
                                )}
                              </div>
                              <Button
                                variant="ghost"
                                className="text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
                                disabled={saving}
                                onClick={async () => {
                                  setSaving(true);
                                  setRoutingMessage(null);
                                  try {
                                    await unsubscribeBrowserPush(subscription.id);
                                    await loadBrowserPushState();
                                    setRoutingMessage({ text: "浏览器设备订阅已移除。", type: "success" });
                                  } catch (error) {
                                    console.error("Failed to remove browser push subscription", error);
                                    setRoutingMessage({ text: "移除浏览器设备失败。", type: "error" });
                                  } finally {
                                    setSaving(false);
                                  }
                                }}
                              >
                                移除
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">安静时段</div>
                <div className="space-y-4 rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">夜间少打扰</div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">常规提醒和汇总类提醒会在这段时间暂停，紧急提醒仍会送达。</div>
                    </div>
                    <Switch
                      checked={Boolean(notificationRouting?.quiet_mode_enabled)}
                      disabled={saving || routingLoading}
                      onCheckedChange={(checked) => void handleRoutingSettingUpdate({ quiet_mode_enabled: checked })}
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="quiet-mode-start" className="text-sm font-medium">开始时间</Label>
                      <Input
                        id="quiet-mode-start"
                        type="time"
                        value={notificationRouting?.quiet_mode_start || ""}
                        disabled={saving || routingLoading}
                        onChange={(e) => {
                          const value = e.target.value;
                          setNotificationRouting((prev) => (prev ? { ...prev, quiet_mode_start: value } : prev));
                        }}
                        onBlur={() => void handleRoutingSettingUpdate({ quiet_mode_start: notificationRouting?.quiet_mode_start || "22:30" }, "静默开始时间已更新。")}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="quiet-mode-end" className="text-sm font-medium">结束时间</Label>
                      <Input
                        id="quiet-mode-end"
                        type="time"
                        value={notificationRouting?.quiet_mode_end || ""}
                        disabled={saving || routingLoading}
                        onChange={(e) => {
                          const value = e.target.value;
                          setNotificationRouting((prev) => (prev ? { ...prev, quiet_mode_end: value } : prev));
                        }}
                        onBlur={() => void handleRoutingSettingUpdate({ quiet_mode_end: notificationRouting?.quiet_mode_end || "07:30" }, "静默结束时间已更新。")}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">每天最多提醒几次</div>
                <div className="mb-3 text-xs text-slate-500 dark:text-slate-400">
                  用更直白的话来说：
                  “紧急提醒” 几乎不限；
                  “重要提醒” 控制在合理范围；
                  “常规提醒”和“汇总提醒” 尽量克制。
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {[
                    { key: "p0_daily_limit" as const, label: "紧急提醒" },
                    { key: "p1_daily_limit" as const, label: "重要提醒" },
                    { key: "p2_daily_limit" as const, label: "常规提醒" },
                    { key: "p3_daily_limit" as const, label: "汇总提醒" },
                  ].map((item) => (
                    <div key={item.key} className="space-y-2 rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                      <Label htmlFor={item.key} className="text-sm font-medium">{item.label}</Label>
                      <Input
                        id={item.key}
                        type="number"
                        min={1}
                        value={String(notificationRouting?.[item.key] ?? "")}
                        disabled={saving || routingLoading}
                        onChange={(e) => {
                          const raw = Number(e.target.value || 1);
                          setNotificationRouting((prev) => (prev ? { ...prev, [item.key]: raw } : prev));
                        }}
                        onBlur={() => {
                          const value = Number(notificationRouting?.[item.key] ?? 1);
                          void handleRoutingSettingUpdate({ [item.key]: Math.max(1, value) }, `${item.label}上限已更新。`);
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-slate-100">发送规则测试</div>
                <div className="mb-3 text-xs text-slate-500 dark:text-slate-400">用模拟通知快速验证：在当前规则下，不同级别的提醒会不会被拦住，会走哪些渠道。</div>
                <div className="flex flex-wrap gap-2">
                  {([
                    { code: "P0", label: "紧急提醒" },
                    { code: "P1", label: "重要提醒" },
                    { code: "P2", label: "常规提醒" },
                    { code: "P3", label: "汇总提醒" },
                  ] as const).map((priority) => (
                    <Button
                      key={priority.code}
                      variant="outline"
                      disabled={Boolean(testingNotificationPriority) || saving || routingLoading}
                      onClick={() => void handleTestNotificationRouting(priority.code)}
                    >
                      {testingNotificationPriority === priority.code ? `${priority.label}测试中...` : `测试${priority.label}`}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          )}
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

  const renderDataSection = () => {
    const marketOptions: Array<{ key: keyof MarketDataSourceConfig; label: string; value: string }> = [
      { key: "a_share", label: "A 股", value: dataSourceConfig?.config.a_share || "YFINANCE" },
      { key: "hk_share", label: "港股", value: dataSourceConfig?.config.hk_share || "YFINANCE" },
      { key: "us_share", label: "美股", value: dataSourceConfig?.config.us_share || "YFINANCE" },
    ];

    return (
      <div className="space-y-6">
        {/* 分市场数据源配置 - 第 1 个 */}
        <div className="rounded-2xl border border-slate-200 px-5 py-5 dark:border-slate-800">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">分市场数据源配置</h3>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                为不同市场选择独立的数据源。默认均使用 YFinance，支持自动故障转移。
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="worker-proxy" className="text-xs text-slate-500 dark:text-slate-400">使用 Cloudflare 代理</Label>
              <Switch
                id="worker-proxy"
                checked={useWorkerProxy}
                onCheckedChange={setUseWorkerProxy}
              />
            </div>
          </div>

          {dataSourceMessage && (
            <div className={`mb-4 rounded-lg px-3 py-2 text-sm ${dataSourceMessage.type === "success" ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-rose-500/10 text-rose-600 dark:text-rose-400"}`}>
              {dataSourceMessage.text}
            </div>
          )}

          {dataSourceTestMessage && (
            <div className={`mb-4 rounded-lg px-3 py-2 text-sm ${dataSourceTestMessage.type === "success" ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-rose-500/10 text-rose-600 dark:text-rose-400"}`}>
              {dataSourceTestMessage.text}
            </div>
          )}

          <div className="space-y-3">
            {marketOptions.map((option) => (
              <div
                key={option.key}
                className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-950"
              >
                <div className="flex-1">
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{option.label}</div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">当前数据源：{option.value}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    value={option.value}
                    onValueChange={(value) => handleDataSourceConfigUpdate(option.key, value)}
                    disabled={savingDataSource || dataSourceLoading}
                  >
                    <SelectTrigger className="w-[120px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {availableDataSources
                        .filter((s) => s.is_available)
                        .map((source) => (
                          <SelectItem key={source.key} value={source.key}>
                            {source.label}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTestDataSource(option.key)}
                    disabled={testingDataSource !== null}
                  >
                    {testingDataSource === option.key ? "测试中..." : "测试"}
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {dataSourceLoading && (
            <div className="mt-4 flex items-center justify-center py-4 text-sm text-slate-500 dark:text-slate-400">
              加载中...
            </div>
          )}
        </div>

        {/* Tavily 搜索 API - 第 2 个 */}
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
              className="md:min-w-33"
            >
              <Save className="mr-2 h-4 w-4" />
              保存配置
            </Button>
            <Button
              variant="outline"
              onClick={handleTestTavily}
              disabled={testingTavily}
              className="md:min-w-33"
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
      </div>
    );
  };

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
              {activeSection === "notifications" && (
                <NotificationSettingsSection
                  authUser={authUser}
                  profile={profile}
                  saving={saving}
                  feishuUrl={feishuUrl}
                  onFeishuUrlChange={setFeishuUrl}
                  onSaveNotificationChannel={handleSaveNotificationChannel}
                  onTestFeishu={handleTestFeishu}
                  testingFeishu={testingFeishu}
                  feishuTestMessage={feishuTestMessage}
                  coreEnabledCount={coreEnabledCount}
                  hasAnyPrimaryChannel={hasAnyPrimaryChannel}
                  notificationReadiness={notificationReadiness}
                  onToggleSwitch={handleToggleSwitch}
                  onApplyNotificationPreset={applyNotificationPreset}
                  advancedNotificationsOpen={advancedNotificationsOpen}
                  onToggleAdvancedNotifications={() => setAdvancedNotificationsOpen((prev) => !prev)}
                  notificationRouting={notificationRouting}
                  browserPushConfig={browserPushConfig}
                  browserPushSubscriptions={browserPushSubscriptions}
                  currentBrowserSubscribed={currentBrowserSubscribed}
                  browserPushLoading={browserPushLoading}
                  routingLoading={routingLoading}
                  routingMessage={routingMessage}
                  onRoutingSettingUpdate={handleRoutingSettingUpdate}
                  onSubscribeCurrentBrowser={handleSubscribeCurrentBrowser}
                  onUnsubscribeCurrentBrowser={handleUnsubscribeCurrentBrowser}
                  onRemoveBrowserSubscription={handleRemoveBrowserSubscription}
                  testingNotificationPriority={testingNotificationPriority}
                  onTestNotificationRouting={handleTestNotificationRouting}
                />
              )}
              {activeSection === "security" && renderSecuritySection()}
              {activeSection === "data" && renderDataSection()}
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
