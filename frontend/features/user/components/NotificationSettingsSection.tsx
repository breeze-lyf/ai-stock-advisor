import { BellRing, ChevronRight, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type {
  BrowserPushConfig,
  BrowserPushSubscriptionItem,
  NotificationRoutingSettings,
} from "@/features/user/api";
import type { UserProfile } from "@/types";

type NotificationMessage = { text: string; type: "success" | "error" } | null;

interface NotificationSettingsSectionProps {
  authUser: UserProfile | null;
  profile: UserProfile | null;
  saving: boolean;
  feishuUrl: string;
  onFeishuUrlChange: (value: string) => void;
  onSaveNotificationChannel: () => void | Promise<void>;
  onTestFeishu: () => void | Promise<void>;
  testingFeishu: boolean;
  feishuTestMessage: NotificationMessage;
  coreEnabledCount: number;
  hasAnyPrimaryChannel: boolean;
  notificationReadiness: "off" | "channel_missing" | "minimal" | "balanced" | "complete";
  onToggleSwitch: (
    key:
      | "notifications_enabled"
      | "enable_price_alerts"
      | "enable_macro_alerts"
      | "enable_strategy_change_alerts"
      | "enable_daily_report"
      | "enable_indicator_alerts"
      | "enable_hourly_summary",
    checked: boolean,
  ) => void | Promise<void>;
  onApplyNotificationPreset: (preset: "light" | "balanced" | "active") => void | Promise<void>;
  advancedNotificationsOpen: boolean;
  onToggleAdvancedNotifications: () => void;
  notificationRouting: NotificationRoutingSettings | null;
  browserPushConfig: BrowserPushConfig | null;
  browserPushSubscriptions: BrowserPushSubscriptionItem[];
  currentBrowserSubscribed: boolean;
  browserPushLoading: boolean;
  routingLoading: boolean;
  routingMessage: NotificationMessage;
  onRoutingSettingUpdate: (patch: Partial<NotificationRoutingSettings>, successText?: string) => void | Promise<void>;
  onSubscribeCurrentBrowser: () => void | Promise<void>;
  onUnsubscribeCurrentBrowser: () => void | Promise<void>;
  onRemoveBrowserSubscription: (subscriptionId: string) => void | Promise<void>;
  testingNotificationPriority: "P0" | "P1" | "P2" | "P3" | null;
  onTestNotificationRouting: (priority: "P0" | "P1" | "P2" | "P3") => void | Promise<void>;
}

export function NotificationSettingsSection({
  authUser,
  profile,
  saving,
  feishuUrl,
  onFeishuUrlChange,
  onSaveNotificationChannel,
  onTestFeishu,
  testingFeishu,
  feishuTestMessage,
  coreEnabledCount,
  hasAnyPrimaryChannel,
  notificationReadiness,
  onToggleSwitch,
  onApplyNotificationPreset,
  advancedNotificationsOpen,
  onToggleAdvancedNotifications,
  notificationRouting,
  browserPushConfig,
  browserPushSubscriptions,
  currentBrowserSubscribed,
  browserPushLoading,
  routingLoading,
  routingMessage,
  onRoutingSettingUpdate,
  onSubscribeCurrentBrowser,
  onUnsubscribeCurrentBrowser,
  onRemoveBrowserSubscription,
  testingNotificationPriority,
  onTestNotificationRouting,
}: NotificationSettingsSectionProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-[28px] border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-emerald-50/70 p-5 shadow-sm dark:border-slate-800 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950/20 md:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-700 dark:border-emerald-900/40 dark:bg-slate-950/50 dark:text-emerald-300">
              <BellRing className="h-3.5 w-3.5" />
              通知体验 2.0
            </div>
            <div className="mt-4 text-xl font-semibold text-slate-900 dark:text-slate-100">通知应该帮你判断轻重，而不是把你淹没</div>
            <div className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              默认只建议保留价格预警、策略变更、宏观重大事件和每日复盘。其他提醒先折叠起来，需要时再打开，这样更接近真实使用时的节奏。
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
              <div className="text-xs text-slate-500 dark:text-slate-400">核心通知已开启</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{coreEnabledCount}/4</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
              <div className="text-xs text-slate-500 dark:text-slate-400">主渠道状态</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{hasAnyPrimaryChannel || feishuUrl.trim() ? "已连接" : "未连接"}</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
              <div className="text-xs text-slate-500 dark:text-slate-400">当前策略密度</div>
              <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                {notificationReadiness === "off" && "已关闭"}
                {notificationReadiness === "channel_missing" && "待连通"}
                {notificationReadiness === "minimal" && "轻提醒"}
                {notificationReadiness === "balanced" && "平衡模式"}
                {notificationReadiness === "complete" && "高覆盖"}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">快速开始</div>
              <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">如果不想逐项判断，就先选一个更接近你使用习惯的模式。</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" disabled={saving} onClick={() => void onApplyNotificationPreset("light")}>轻提醒</Button>
              <Button variant="outline" disabled={saving} onClick={() => void onApplyNotificationPreset("balanced")}>平衡模式</Button>
              <Button variant="outline" disabled={saving} onClick={() => void onApplyNotificationPreset("active")}>高敏感模式</Button>
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {[
              { title: "轻提醒", description: "只保留更关键的风险与变化提醒。" },
              { title: "平衡模式", description: "覆盖关键场景，同时尽量不打扰。" },
              { title: "高敏感模式", description: "适合更高频地跟踪市场与仓位。" },
            ].map((item) => (
              <div key={item.title} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-800 dark:bg-slate-950/60">
                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">{item.description}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:p-6">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">当前状态</div>
          <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-4 dark:bg-slate-950/60">
            <div className="font-medium text-slate-900 dark:text-slate-100">
              {notificationReadiness === "off" && "通知总开关已关闭"}
              {notificationReadiness === "channel_missing" && "还没真正连上通知渠道"}
              {notificationReadiness === "minimal" && "当前配置比较克制"}
              {notificationReadiness === "balanced" && "当前配置比较均衡"}
              {notificationReadiness === "complete" && "当前配置已经比较完整"}
            </div>
            <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">
              {notificationReadiness === "off" && "系统不会主动推送任何提醒。"}
              {notificationReadiness === "channel_missing" && "建议至少连接飞书或浏览器推送，否则很多提醒虽然被触发，但没有出口。"}
              {notificationReadiness === "minimal" && "适合不想被频繁打断，但仍希望收到关键提醒的人。"}
              {notificationReadiness === "balanced" && "这会是大多数人的默认舒服区。"}
              {notificationReadiness === "complete" && "覆盖面最全，但行情剧烈时收到的提醒也会更多。"}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-4 dark:border-slate-800">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">全局通知开关</div>
              <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">关闭后，系统不会再主动发出任何自动提醒。</div>
            </div>
            <Switch
              checked={Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true)}
              disabled={saving}
              onCheckedChange={(checked) => void onToggleSwitch("notifications_enabled", checked)}
              className="data-[state=checked]:bg-emerald-500"
            />
          </div>
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:p-6">
        <div className="mb-4">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">核心通知</div>
          <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">先把最值得默认开启的四类提醒稳定下来，再考虑补充型通知。</div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {[
            { key: "enable_price_alerts" as const, title: "价格预警", description: "到达止盈止损位时第一时间提醒。", tone: "from-emerald-50 to-white dark:from-emerald-950/20 dark:to-slate-900" },
            { key: "enable_macro_alerts" as const, title: "全球宏观提醒", description: "推送影响全球市场的大事件与风险。", tone: "from-sky-50 to-white dark:from-sky-950/20 dark:to-slate-900" },
            { key: "enable_strategy_change_alerts" as const, title: "策略变更", description: "盘后复盘发现操作建议显著变化时提醒。", tone: "from-violet-50 to-white dark:from-violet-950/20 dark:to-slate-900" },
            { key: "enable_daily_report" as const, title: "每日复盘报告", description: "每天给你一份更完整的持仓体检。", tone: "from-slate-50 to-white dark:from-slate-950 dark:to-slate-900" },
          ].map((item) => (
            <div key={item.key} className={`rounded-2xl border border-slate-200 bg-gradient-to-br p-4 dark:border-slate-800 ${item.tone}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                  <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">{item.description}</div>
                </div>
                <Switch
                  checked={Boolean(profile?.[item.key] ?? authUser?.[item.key])}
                  disabled={saving || !Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true)}
                  onCheckedChange={(checked) => void onToggleSwitch(item.key, checked)}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:p-6">
        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <Label htmlFor="feishu-webhook" className="text-sm font-semibold text-slate-900 dark:text-slate-100">飞书机器人 Webhook</Label>
            <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">飞书仍然是最适合接收关键提醒的主渠道，尤其适合价格预警和策略变化。</div>
            <Input id="feishu-webhook" className="mt-3" type="text" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." value={feishuUrl} onChange={(e) => onFeishuUrlChange(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => void onSaveNotificationChannel()} disabled={saving}>
                <Save className="mr-2 h-4 w-4" />
                保存通知通道
              </Button>
              <Button variant="outline" onClick={() => void onTestFeishu()} disabled={testingFeishu}>
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

          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-800 dark:bg-slate-950/60">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">你现在最可能需要什么</div>
            <div className="mt-3 space-y-3 text-xs leading-6 text-slate-500 dark:text-slate-400">
              <div>如果你主要担心错过关键价格位，先保证价格预警和飞书是开的。</div>
              <div>如果你更怕节奏被打乱，建议先用“平衡模式”，再决定是否打开整点摘要。</div>
              <div>如果你经常在电脑前工作，再补上浏览器推送，会比邮件更及时。</div>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:p-6">
        <button type="button" className="flex w-full items-center justify-between text-left" onClick={onToggleAdvancedNotifications}>
          <div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">高级通知设置</div>
            <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">技术指标、整点摘要、渠道路由、浏览器设备、安静时段和频控都放在这里，默认折叠，避免第一次就把用户压住。</div>
          </div>
          <ChevronRight className={`h-4 w-4 text-slate-500 transition-transform ${advancedNotificationsOpen ? "rotate-90" : ""}`} />
        </button>

        {advancedNotificationsOpen && (
          <div className="mt-5 space-y-6 border-t border-slate-200 pt-5 dark:border-slate-800">
            <div className="grid gap-4 md:grid-cols-2">
              {[
                { key: "enable_indicator_alerts" as const, title: "技术指标提醒", description: "RSI 等指标进入极端区间时提醒，更适合盯盘型用户。" },
                { key: "enable_hourly_summary" as const, title: "整点摘要", description: "每小时推送一次新闻与行情总结，信息量更大。" },
              ].map((item) => (
                <div key={item.key} className="rounded-2xl border border-slate-200 px-4 py-4 dark:border-slate-800">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                      <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">{item.description}</div>
                    </div>
                    <Switch
                      checked={Boolean(profile?.[item.key] ?? authUser?.[item.key])}
                      disabled={saving || !Boolean(profile?.notifications_enabled ?? authUser?.notifications_enabled ?? true)}
                      onCheckedChange={(checked) => void onToggleSwitch(item.key, checked)}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div>
              <div className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-100">通知渠道</div>
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

              <div className="grid gap-3 md:grid-cols-3">
                {[
                  { key: "feishu_enabled" as const, title: "飞书", description: "最适合接收关键提醒，及时且到达率更高。" },
                  { key: "email_enabled" as const, title: "邮件", description: "更适合日报、复盘和偏长内容。" },
                  { key: "browser_push_enabled" as const, title: "浏览器弹窗", description: "适合办公时即时看到，但需要先订阅当前浏览器。" },
                ].map((item) => (
                  <div key={item.key} className="rounded-2xl border border-slate-200 px-4 py-4 dark:border-slate-800">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                        <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">{item.description}</div>
                      </div>
                      <Switch
                        checked={Boolean(notificationRouting?.[item.key])}
                        disabled={saving || routingLoading}
                        onCheckedChange={(checked) => void onRoutingSettingUpdate({ [item.key]: checked })}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">当前浏览器订阅</div>
                  <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">
                    {browserPushConfig?.web_push_enabled
                      ? currentBrowserSubscribed
                        ? "这台浏览器已经有订阅凭证，可以接收桌面提醒。"
                        : "这台浏览器还没订阅，需要点一下右侧按钮。"
                      : "当前环境还没配置 Web Push 所需密钥，所以这里暂时不可用。"}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" disabled={saving || browserPushLoading || !browserPushConfig?.web_push_enabled} onClick={() => void onSubscribeCurrentBrowser()}>
                    {saving && !currentBrowserSubscribed ? "连接中..." : "连接当前浏览器"}
                  </Button>
                  <Button variant="ghost" disabled={saving || browserPushLoading || (!currentBrowserSubscribed && browserPushSubscriptions.length === 0)} onClick={() => void onUnsubscribeCurrentBrowser()}>
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
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{subscription.device_name || "未命名设备"}</div>
                            <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                              {subscription.browser || "未知浏览器"} · 注册于 {new Date(subscription.created_at).toLocaleString("zh-CN")}
                            </div>
                            {subscription.last_used_at && (
                              <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">最近活跃：{new Date(subscription.last_used_at).toLocaleString("zh-CN")}</div>
                            )}
                          </div>
                          <Button variant="ghost" size="sm" className="text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300" disabled={saving} onClick={() => void onRemoveBrowserSubscription(subscription.id)}>
                            移除
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">安静时段</div>
                <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">P2/P3 这类不紧急的提醒会尽量避开这段时间。</div>
                <div className="mt-4 flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-4 dark:bg-slate-950/60">
                  <div className="text-sm text-slate-600 dark:text-slate-300">启用安静时段</div>
                  <Switch
                    checked={Boolean(notificationRouting?.quiet_mode_enabled)}
                    disabled={saving || routingLoading}
                    onCheckedChange={(checked) => void onRoutingSettingUpdate({ quiet_mode_enabled: checked })}
                  />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="quiet-start">开始时间</Label>
                    <Input id="quiet-start" type="time" value={notificationRouting?.quiet_mode_start || "22:30"} onChange={(event) => void onRoutingSettingUpdate({ quiet_mode_start: event.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="quiet-end">结束时间</Label>
                    <Input id="quiet-end" type="time" value={notificationRouting?.quiet_mode_end || "08:00"} onChange={(event) => void onRoutingSettingUpdate({ quiet_mode_end: event.target.value })} />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">每日上限</div>
                <div className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">优先级越低，建议上限越保守，避免提醒疲劳。</div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[
                    { key: "p0_daily_limit" as const, title: "紧急提醒", label: "P0" },
                    { key: "p1_daily_limit" as const, title: "重要提醒", label: "P1" },
                    { key: "p2_daily_limit" as const, title: "常规提醒", label: "P2" },
                    { key: "p3_daily_limit" as const, title: "汇总提醒", label: "P3" },
                  ].map((item) => (
                    <div key={item.key} className="rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-800">
                      <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">{item.title}</div>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.label}</div>
                      <Input
                        className="mt-3"
                        type="number"
                        min={1}
                        defaultValue={String(notificationRouting?.[item.key] ?? 1)}
                        disabled={saving || routingLoading}
                        onBlur={(event) => {
                          const value = Math.max(1, Number(event.target.value || 1));
                          void onRoutingSettingUpdate({ [item.key]: value }, `${item.label} 上限已更新。`);
                        }}
                      />
                    </div>
                  ))}
                </div>
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
                  <Button key={priority.code} variant="outline" disabled={Boolean(testingNotificationPriority) || saving || routingLoading} onClick={() => void onTestNotificationRouting(priority.code)}>
                    {testingNotificationPriority === priority.code ? `${priority.label}测试中...` : `测试${priority.label}`}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
