"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { getProfile, updateSettings, UserProfile } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, Save, Key, Database, Cpu, Clock, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export default function SettingsPage() {
    const { isAuthenticated } = useAuth();
    const { theme: currentTheme, setTheme } = useTheme();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [geminiKey, setGeminiKey] = useState("");
    const [feishuUrl, setFeishuUrl] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null);

    useEffect(() => {
        if (isAuthenticated) {
            loadProfile();
        }
    }, [isAuthenticated]);

    const loadProfile = async () => {
        try {
            const data = await getProfile();
            setProfile(data);
            if (data.feishu_webhook_url) setFeishuUrl(data.feishu_webhook_url);
            // Sync theme from backend if needed
            if (data.theme && currentTheme !== data.theme) {
                setTheme(data.theme);
            }
        } catch (error) {
            console.error("Failed to load profile", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveKeys = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const payload: any = {};
            if (geminiKey) payload.api_key_gemini = geminiKey;
            if (feishuUrl !== profile?.feishu_webhook_url) payload.feishu_webhook_url = feishuUrl;

            if (Object.keys(payload).length === 0) {
                setSaving(false);
                return;
            }

            await updateSettings(payload);

            setMessage({ text: "API Keys updated successfully!", type: "success" });
            setGeminiKey("");
            loadProfile();
        } catch (error) {
            setMessage({ text: "Failed to update settings.", type: "error" });
        } finally {
            setSaving(false);
        }
    };

    const handleModelUpdate = async (model: string) => {
        setSaving(true);
        try {
            await updateSettings({
                preferred_ai_model: model
            });
            loadProfile();
            setMessage({ text: `Preferred content switched to ${model}`, type: "success" });
        } catch (error) {
            console.error("Failed to update model", error);
        } finally {
            setSaving(false);
        }
    };

    const handleTimezoneUpdate = async (timezone: string) => {
        setSaving(true);
        try {
            await updateSettings({
                timezone: timezone
            });
            loadProfile();
            setMessage({ text: `Timezone updated to ${timezone}`, type: "success" });
        } catch (error) {
            console.error("Failed to update timezone", error);
            setMessage({ text: "Failed to update timezone.", type: "error" });
        } finally {
            setSaving(false);
        }
    };    const handleThemeUpdate = async (theme: string) => {
        setSaving(true);
        setTheme(theme);
        try {
            await updateSettings({
                theme: theme
            });
            loadProfile();
            setMessage({ text: `Visual theme updated to ${theme}`, type: "success" });
        } catch (error) {
            console.error("Failed to update theme", error);
            setMessage({ text: "Failed to update theme.", type: "error" });
        } finally {
            setSaving(false);
        }
    };

    const handleToggleSwitch = async (key: keyof UserProfile, value: boolean) => {
        setSaving(true);
        try {
            await updateSettings({
                [key]: value
            });
            loadProfile();
            setMessage({ text: "Notification preference updated.", type: "success" });
        } catch (error) {
            console.error("Failed to update notification setting", error);
            setMessage({ text: "Failed to update notification setting.", type: "error" });
        } finally {
            setSaving(false);
        }
    };


    if (loading) return <div className="p-8">Loading settings...</div>;

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-8">
            <div className="max-w-4xl mx-auto space-y-6">
                <div className="flex items-center gap-4">
                    <Link href="/">
                        <Button variant="ghost" size="icon">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                    </Link>
                    <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                </div>

                {message && (
                    <div className={`p-4 rounded-md border ${message.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                        {message.text}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Moon className="h-5 w-5 text-slate-400 dark:text-slate-500" />
                                    Visual Theme
                                </CardTitle>
                                <CardDescription>
                                    Switch between light and dark modes.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="grid grid-cols-3 gap-2">
                                <Button 
                                    variant={currentTheme === 'light' ? 'default' : 'outline'} 
                                    className="flex items-center gap-2 h-20 flex-col"
                                    onClick={() => handleThemeUpdate('light')}
                                    disabled={saving}
                                >
                                    <Sun className="h-5 w-5" />
                                    <span className="text-xs">Light</span>
                                </Button>
                                <Button 
                                    variant={currentTheme === 'dark' ? 'default' : 'outline'} 
                                    className="flex items-center gap-2 h-20 flex-col"
                                    onClick={() => handleThemeUpdate('dark')}
                                    disabled={saving}
                                >
                                    <Moon className="h-5 w-5" />
                                    <span className="text-xs">Dark</span>
                                </Button>
                                <Button 
                                    variant={currentTheme === 'system' ? 'default' : 'outline'} 
                                    className="flex items-center gap-2 h-20 flex-col"
                                    onClick={() => handleThemeUpdate('system')}
                                    disabled={saving}
                                >
                                    <Cpu className="h-5 w-5" />
                                    <span className="text-xs">Auto</span>
                                </Button>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Key className="h-5 w-5" />
                                    API Key Management
                                </CardTitle>
                                <CardDescription>
                                    Configure your own AI API Keys.
                                </CardDescription>
                            </CardHeader>
                            <form onSubmit={handleSaveKeys}>
                                <CardContent className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="gemini">Google Gemini Key</Label>
                                        <Input
                                            id="gemini"
                                            type="password"
                                            placeholder="AIzaSy..."
                                            value={geminiKey}
                                            onChange={(e) => setGeminiKey(e.target.value)}
                                        />
                                        <div className="text-[10px] text-muted-foreground flex justify-between">
                                            <span>Status: {profile?.has_gemini_key ? "✅ Set" : "⚠️ Not Set"}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2 pt-4 border-t border-slate-100 dark:border-slate-800">
                                        <Label htmlFor="feishu" className="flex items-center gap-2">
                                            飞书机器人 Webhook (私人)
                                        </Label>
                                        <Input
                                            id="feishu"
                                            type="text"
                                            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                                            value={feishuUrl}
                                            onChange={(e) => setFeishuUrl(e.target.value)}
                                        />
                                        <CardDescription className="text-[10px]">
                                            不配飞书地址的用户将不会启动 AI 自动化分析与汇总，以节省 API 额度。
                                        </CardDescription>
                                    </div>
                                </CardContent>
                                <CardFooter>
                                    <Button type="submit" className="w-full" disabled={saving || (!geminiKey && feishuUrl === profile?.feishu_webhook_url)}>
                                        {saving ? "Saving..." : "Save Settings"}
                                        <Save className="ml-2 h-4 w-4" />
                                    </Button>
                                </CardFooter>
                            </form>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Clock className="h-5 w-5" />
                                    推送偏好设置
                                </CardTitle>
                                <CardDescription>
                                    精细化控制飞书机器人的推送频率与类别。
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {[
                                    { id: 'enable_price_alerts', label: '价格/风险预警', desc: '触达止盈止损或指标极端值时推送', key: 'enable_price_alerts' as const },
                                    { id: 'enable_hourly_summary', label: '持仓整点摘要', desc: '每小时针对持仓标的进行全网新闻精要汇总', key: 'enable_hourly_summary' as const },
                                    { id: 'enable_daily_report', label: '每日持仓报告', desc: '北京时间 09:00/22:00 生成深度持仓体检报告', key: 'enable_daily_report' as const },
                                    { id: 'enable_macro_alerts', label: '全球宏观变动', desc: '实时监控并推送影响全球市场的宏观大事件', key: 'enable_macro_alerts' as const },
                                ].map((item) => (
                                    <div key={item.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                                        <div className="space-y-0.5">
                                            <Label htmlFor={item.id} className="text-sm font-medium">{item.label}</Label>
                                            <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                                        </div>
                                        <button
                                            id={item.id}
                                            onClick={() => handleToggleSwitch(item.key, !profile?.[item.key])}
                                            disabled={saving}
                                            title={`Toggle ${item.label}`}
                                            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${profile?.[item.key] ? 'bg-emerald-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                                        >
                                            <span className={`pointer-events-none block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${profile?.[item.key] ? 'translate-x-4' : 'translate-x-0.5'}`} />
                                        </button>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>

                    <div className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Cpu className="h-5 w-5" />
                                    AI Model Selection
                                </CardTitle>
                                <CardDescription>
                                    Choose which model to use for stock analysis.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="model-select">Preferred Analysis Model</Label>
                                    <select
                                        id="model-select"
                                        className="w-full p-2 rounded-md border border-slate-200 dark:border-slate-800 bg-transparent text-sm"
                                        value={profile?.preferred_ai_model || "gemini-1.5-flash"}
                                        onChange={(e) => handleModelUpdate(e.target.value)}
                                        disabled={saving}
                                        title="Select AI Model"
                                    >
                                        <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fast/Default)</option>
                                        <option value="deepseek-v3">DeepSeek V3 (Reasoning/SF)</option>
                                        <option value="deepseek-r1">DeepSeek R1 (Thought/SF)</option>
                                        <option value="qwen-2.5-72b">Qwen 2.5 72B (Versatile/SF)</option>
                                        <option value="qwen-3-vl-thinking">Qwen 3 VL (Reasoning/Thinking/SF)</option>
                                    </select>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Note: SiliconFlow models use the system-managed API Key. You only need to provide your own Gemini Key if you use Gemini models.
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Clock className="h-5 w-5" />
                                    Timezone Configuration
                                </CardTitle>
                                <CardDescription>
                                    Set your preferred timezone for all displays.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="timezone-select">System Global Timezone</Label>
                                    <select
                                        id="timezone-select"
                                        className="w-full p-2 rounded-md border border-slate-200 dark:border-slate-800 bg-transparent text-sm"
                                        value={profile?.timezone || "Asia/Shanghai"}
                                        onChange={(e) => handleTimezoneUpdate(e.target.value)}
                                        disabled={saving}
                                        title="Select System Timezone"
                                    >
                                        <optgroup label="亚洲 (Asia)">
                                            <option value="Asia/Shanghai">北京 / 上海 (UTC+8)</option>
                                            <option value="Asia/Hong_Kong">香港 / 台北 (UTC+8)</option>
                                            <option value="Asia/Tokyo">东京 / 首尔 (UTC+9)</option>
                                            <option value="Asia/Singapore">新加坡 (UTC+8)</option>
                                            <option value="Asia/Dubai">迪拜 (UTC+4)</option>
                                        </optgroup>
                                        <optgroup label="美洲 (Americas)">
                                            <option value="America/New_York">纽约 / 华盛顿 (EST/EDT)</option>
                                            <option value="America/Chicago">芝加哥 (CST/CDT)</option>
                                            <option value="America/Los_Angeles">洛杉矶 / 旧金山 (PST/PDT)</option>
                                            <option value="America/Toronto">多伦多 (EST/EDT)</option>
                                        </optgroup>
                                        <optgroup label="欧洲 (Europe)">
                                            <option value="Europe/London">伦敦 / GMT (UTC+0/+1)</option>
                                            <option value="Europe/Paris">巴黎 / 柏林 / 罗马 (UTC+1/+2)</option>
                                            <option value="Europe/Zurich">苏黎世 (UTC+1/+2)</option>
                                            <option value="Europe/Moscow">莫斯科 (UTC+3)</option>
                                        </optgroup>
                                        <optgroup label="大洋洲 (Oceania)">
                                            <option value="Australia/Sydney">悉尼 / 墨尔本 (UTC+10/+11)</option>
                                            <option value="Pacific/Auckland">奥克兰 (UTC+12/+13)</option>
                                        </optgroup>
                                        <optgroup label="标准 (Standard)">
                                            <option value="UTC">UTC (Universal Coordinated Time)</option>
                                        </optgroup>
                                    </select>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    This will affect Smart Alert Stream, Macro Radar, and all historical data charts.
                                </p>
                            </CardContent>
                        </Card>

                    </div>
                </div>
            </div>
        </div>
    );
}
