"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { getProfile, updateSettings, UserProfile } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, Save, Key, Database } from "lucide-react";

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

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            if (!geminiKey) return; // Don't verify empty submission for now

            await updateSettings({
                api_key_gemini: geminiKey
            });

            setMessage({ text: "Settings updated successfully!", type: "success" });
            setGeminiKey(""); // Clear input after save
            loadProfile(); // Reload to update status
        } catch (error) {
            setMessage({ text: "Failed to update settings.", type: "error" });
        } finally {
            setSaving(false);
        }
    };

    const handleSourceUpdate = async (source: "ALPHA_VANTAGE" | "YFINANCE") => {
        try {
            await updateSettings({
                preferred_data_source: source
            });
            loadProfile();
        } catch (error) {
            console.error("Failed to update source", error);
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

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Key className="h-5 w-5" />
                            API Key Management
                        </CardTitle>
                        <CardDescription>
                            Configure your own AI API Keys to unlock infinite analysis.
                            Your keys are encrypted and stored securely.
                        </CardDescription>
                    </CardHeader>
                    <form onSubmit={handleSave}>
                        <CardContent className="space-y-4">
                            {message && (
                                <div className={`p-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                    {message.text}
                                </div>
                            )}

                            <div className="space-y-2">
                                <Label htmlFor="gemini">Google Gemini API Key</Label>
                                <div className="flex gap-2">
                                    <Input
                                        id="gemini"
                                        type="password"
                                        placeholder="Enter your AIzaSy... key"
                                        value={geminiKey}
                                        onChange={(e) => setGeminiKey(e.target.value)}
                                    />
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    Status: {profile?.has_gemini_key ? (
                                        <span className="text-green-600 font-medium">✅ Configured</span>
                                    ) : (
                                        <span className="text-yellow-600 font-medium">⚠️ Not Set (Using System Mock/Quota)</span>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter>
                            <Button type="submit" disabled={saving || !geminiKey}>
                                {saving ? "Saving..." : "Save API Key"}
                                <Save className="ml-2 h-4 w-4" />
                            </Button>
                        </CardFooter>
                    </form>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5" />
                            Data Source Preference
                        </CardTitle>
                        <CardDescription>
                            Choose which provider to use for real-time stock codes.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex gap-4">
                            <Button
                                variant={profile?.preferred_data_source === "ALPHA_VANTAGE" ? "default" : "outline"}
                                onClick={() => handleSourceUpdate("ALPHA_VANTAGE")}
                                className="flex-1 h-20 flex flex-col items-center justify-center gap-1"
                                disabled={saving}
                            >
                                <span className="font-bold">Alpha Vantage</span>
                                <span className="text-[10px] opacity-70">Official API (Stable, 25 req/day)</span>
                            </Button>
                            <Button
                                variant={profile?.preferred_data_source === "YFINANCE" ? "default" : "outline"}
                                onClick={() => handleSourceUpdate("YFINANCE")}
                                className="flex-1 h-20 flex flex-col items-center justify-center gap-1"
                                disabled={saving}
                            >
                                <span className="font-bold">Yahoo Finance</span>
                                <span className="text-[10px] opacity-70">Scraper (Unlimited, but prone to blocks)</span>
                            </Button>
                        </div>
                        <p className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-900 p-3 rounded italic">
                            Tip: If you're in a region with poor connectivity to Yahoo, Alpha Vantage is highly recommended.
                            If the preferred source fails, the system will automatically fall back to the other one.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
