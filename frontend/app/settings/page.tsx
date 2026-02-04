"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { getProfile, updateSettings, UserProfile } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, Save, Key, Database, Cpu } from "lucide-react";

export default function SettingsPage() {
    const { isAuthenticated } = useAuth();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [geminiKey, setGeminiKey] = useState("");
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
                                </CardContent>
                                <CardFooter>
                                    <Button type="submit" className="w-full" disabled={saving || !geminiKey}>
                                        {saving ? "Saving..." : "Save Keys"}
                                        <Save className="ml-2 h-4 w-4" />
                                    </Button>
                                </CardFooter>
                            </form>
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
                                    <Label>Preferred Analysis Model</Label>
                                    <select
                                        className="w-full p-2 rounded-md border border-slate-200 dark:border-slate-800 bg-transparent text-sm"
                                        value={profile?.preferred_ai_model || "gemini-1.5-flash"}
                                        onChange={(e) => handleModelUpdate(e.target.value)}
                                        disabled={saving}
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

                    </div>
                </div>
            </div>
        </div>
    );
}
