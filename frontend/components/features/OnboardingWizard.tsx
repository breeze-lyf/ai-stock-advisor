"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/shared/api/client";

export type InvestmentProfile = "CONSERVATIVE" | "BALANCED" | "AGGRESSIVE";
export type MarketPreference = "A_SHARE" | "HK_SHARE" | "US_SHARE";
export type NotificationFrequency = "REALTIME" | "HOURLY" | "DAILY" | "NEVER";

interface OnboardingData {
    investmentProfile: InvestmentProfile;
    preferredMarkets: MarketPreference[];
    notificationFrequency: NotificationFrequency;
    riskToleranceScore: number;
    investmentExperienceYears: number;
    targetAnnualReturn: number;
}

interface OnboardingWizardProps {
    onComplete?: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const [data, setData] = useState<OnboardingData>({
        investmentProfile: "BALANCED",
        preferredMarkets: ["A_SHARE"],
        notificationFrequency: "REALTIME",
        riskToleranceScore: 5,
        investmentExperienceYears: 0,
        targetAnnualReturn: 10,
    });

    const handleNext = () => setStep(s => s + 1);
    const handleBack = () => setStep(s => s - 1);

    const handleSubmit = async () => {
        setLoading(true);
        setError("");

        try {
            await api.post("/api/v1/user-preferences/onboarding", {
                investment_profile: data.investmentProfile,
                preferred_markets: data.preferredMarkets,
                notification_frequency: data.notificationFrequency,
                risk_tolerance_score: data.riskToleranceScore,
                investment_experience_years: data.investmentExperienceYears,
                target_annual_return: data.targetAnnualReturn,
            });
            onComplete?.();
            router.push("/");
        } catch (err: any) {
            setError(err.response?.data?.detail || "提交失败，请重试");
        } finally {
            setLoading(false);
        }
    };

    const renderStep1 = () => (
        <div className="space-y-6">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                    选择您的投资偏好
                </h2>
                <p className="text-slate-500 dark:text-slate-400">
                    这将帮助我们为您提供更合适的投资建议
                </p>
            </div>

            <div className="grid gap-4">
                {/* 保守型 */}
                <button
                    onClick={() => setData({ ...data, investmentProfile: "CONSERVATIVE" })}
                    className={`p-4 rounded-xl border-2 transition-all ${
                        data.investmentProfile === "CONSERVATIVE"
                            ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                            : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
                    }`}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                            data.investmentProfile === "CONSERVATIVE"
                                ? "bg-emerald-500 text-white"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                        }`}>
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <div className="text-left">
                            <h3 className="font-semibold text-slate-900 dark:text-slate-100">保守型</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                追求本金安全，能接受较低收益
                            </p>
                        </div>
                    </div>
                </button>

                {/* 稳健型 */}
                <button
                    onClick={() => setData({ ...data, investmentProfile: "BALANCED" })}
                    className={`p-4 rounded-xl border-2 transition-all ${
                        data.investmentProfile === "BALANCED"
                            ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                            : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
                    }`}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                            data.investmentProfile === "BALANCED"
                                ? "bg-emerald-500 text-white"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                        }`}>
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                            </svg>
                        </div>
                        <div className="text-left">
                            <h3 className="font-semibold text-slate-900 dark:text-slate-100">稳健型</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                平衡风险与收益，追求长期稳定增长
                            </p>
                        </div>
                    </div>
                </button>

                {/* 激进型 */}
                <button
                    onClick={() => setData({ ...data, investmentProfile: "AGGRESSIVE" })}
                    className={`p-4 rounded-xl border-2 transition-all ${
                        data.investmentProfile === "AGGRESSIVE"
                            ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                            : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
                    }`}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                            data.investmentProfile === "AGGRESSIVE"
                                ? "bg-emerald-500 text-white"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                        }`}>
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div className="text-left">
                            <h3 className="font-semibold text-slate-900 dark:text-slate-100">激进型</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                追求高收益，能承受较大波动
                            </p>
                        </div>
                    </div>
                </button>
            </div>

            <div className="flex justify-end pt-4">
                <button
                    onClick={handleNext}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors"
                >
                    下一步
                </button>
            </div>
        </div>
    );

    const renderStep2 = () => (
        <div className="space-y-6">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                    选择关注的市场
                </h2>
                <p className="text-slate-500 dark:text-slate-400">
                    至少选择一个市场
                </p>
            </div>

            <div className="grid gap-3">
                {["A_SHARE", "HK_SHARE", "US_SHARE"].map((market) => (
                    <button
                        key={market}
                        onClick={() => {
                            const markets = data.preferredMarkets.includes(market as MarketPreference)
                                ? data.preferredMarkets.filter(m => m !== market)
                                : [...data.preferredMarkets, market as MarketPreference];
                            if (markets.length > 0) {
                                setData({ ...data, preferredMarkets: markets });
                            }
                        }}
                        className={`p-4 rounded-xl border-2 transition-all flex items-center justify-between ${
                            data.preferredMarkets.includes(market as MarketPreference)
                                ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
                                : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
                        }`}
                    >
                        <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                data.preferredMarkets.includes(market as MarketPreference)
                                    ? "bg-emerald-500 text-white"
                                    : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                            }`}>
                                {market === "A_SHARE" && "🇨🇳"}
                                {market === "HK_SHARE" && "🇭🇰"}
                                {market === "US_SHARE" && "🇺🇸"}
                            </div>
                            <div className="text-left">
                                <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                                    {market === "A_SHARE" && "A 股"}
                                    {market === "HK_SHARE" && "港股"}
                                    {market === "US_SHARE" && "美股"}
                                </h3>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    {market === "A_SHARE" && "上海证券交易所、深圳证券交易所"}
                                    {market === "HK_SHARE" && "香港交易所"}
                                    {market === "US_SHARE" && "纽约证券交易所、纳斯达克"}
                                </p>
                            </div>
                        </div>
                        {data.preferredMarkets.includes(market as MarketPreference) && (
                            <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        )}
                    </button>
                ))}
            </div>

            <div className="flex justify-between pt-4">
                <button
                    onClick={handleBack}
                    className="px-6 py-2.5 text-slate-600 dark:text-slate-400 font-medium rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                    返回
                </button>
                <button
                    onClick={handleNext}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors"
                >
                    下一步
                </button>
            </div>
        </div>
    );

    const renderStep3 = () => (
        <div className="space-y-6">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                    风险承受能力评估
                </h2>
                <p className="text-slate-500 dark:text-slate-400">
                    选择 1-10 分，10 分代表最能承受风险
                </p>
            </div>

            <div className="space-y-4">
                <div className="flex justify-between text-sm text-slate-500 dark:text-slate-400">
                    <span>保守 (1)</span>
                    <span>激进 (10)</span>
                </div>
                <div className="grid grid-cols-10 gap-2">
                    {Array.from({ length: 10 }, (_, i) => i + 1).map((score) => (
                        <button
                            key={score}
                            onClick={() => setData({ ...data, riskToleranceScore: score })}
                            className={`h-12 rounded-lg font-semibold transition-all ${
                                data.riskToleranceScore === score
                                    ? "bg-emerald-500 text-white scale-110"
                                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                            }`}
                        >
                            {score}
                        </button>
                    ))}
                </div>
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800 text-center">
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                        您的选择：<span className="font-bold text-emerald-600 dark:text-emerald-400">{data.riskToleranceScore}</span>
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                        {data.riskToleranceScore <= 3 && "保守型：优先保本，能接受 1-5% 的年化收益"}
                        {data.riskToleranceScore >= 4 && data.riskToleranceScore <= 7 && "稳健型：平衡风险，追求 5-15% 的年化收益"}
                        {data.riskToleranceScore >= 8 && "激进型：追求高收益，能承受 20%+ 的波动"}
                    </p>
                </div>
            </div>

            <div className="flex justify-between pt-4">
                <button
                    onClick={handleBack}
                    className="px-6 py-2.5 text-slate-600 dark:text-slate-400 font-medium rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                    返回
                </button>
                <button
                    onClick={handleNext}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors"
                >
                    下一步
                </button>
            </div>
        </div>
    );

    const renderStep4 = () => (
        <div className="space-y-6">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                    投资经验与目标
                </h2>
                <p className="text-slate-500 dark:text-slate-400">
                    帮助我们了解您的投资背景
                </p>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        投资经验年数
                    </label>
                    <select
                        value={data.investmentExperienceYears}
                        onChange={(e) => setData({ ...data, investmentExperienceYears: parseInt(e.target.value) })}
                        className="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500"
                    >
                        <option value={0}>新手入门（0 年）</option>
                        <option value={1}>1 年</option>
                        <option value={2}>2 年</option>
                        <option value={3}>3-5 年</option>
                        <option value={6}>6-10 年</option>
                        <option value={11}>10 年以上</option>
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        期望年化收益率 (%)
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={data.targetAnnualReturn}
                        onChange={(e) => setData({ ...data, targetAnnualReturn: parseInt(e.target.value) })}
                        className="w-full"
                    />
                    <div className="text-center mt-2">
                        <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data.targetAnnualReturn}%</span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-500 text-center mt-1">
                        {data.targetAnnualReturn <= 10 && "稳健目标，主要通过固定收益和蓝筹股实现"}
                        {data.targetAnnualReturn > 10 && data.targetAnnualReturn <= 20 && "进取目标，需要承担中等风险"}
                        {data.targetAnnualReturn > 20 && "高目标，需要承担较高风险，建议 diversified portfolio"}
                    </p>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        通知频率
                    </label>
                    <select
                        value={data.notificationFrequency}
                        onChange={(e) => setData({ ...data, notificationFrequency: e.target.value as NotificationFrequency })}
                        className="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500"
                    >
                        <option value="REALTIME">实时推送（重要消息立即通知）</option>
                        <option value="HOURLY">每小时摘要（整点推送）</option>
                        <option value="DAILY">每日报告（盘后汇总）</option>
                        <option value="NEVER">免打扰（不推送）</option>
                    </select>
                </div>
            </div>

            <div className="flex justify-between pt-4">
                <button
                    onClick={handleBack}
                    className="px-6 py-2.5 text-slate-600 dark:text-slate-400 font-medium rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                    返回
                </button>
                <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-medium rounded-lg transition-colors"
                >
                    {loading ? "提交中..." : "开始使用"}
                </button>
            </div>

            {error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
                    {error}
                </div>
            )}
        </div>
    );

    const renderProgress = () => (
        <div className="flex items-center justify-between mb-8">
            {[1, 2, 3, 4].map((s) => (
                <div key={s} className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                        s === step
                            ? "bg-emerald-500 text-white"
                            : s < step
                            ? "bg-emerald-200 dark:bg-emerald-800 text-emerald-600 dark:text-emerald-400"
                            : "bg-slate-200 dark:bg-slate-700 text-slate-500"
                    }`}>
                        {s < step ? (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        ) : (
                            s
                        )}
                    </div>
                    {s < 4 && (
                        <div className={`w-12 h-1 ${
                            s < step ? "bg-emerald-500" : "bg-slate-200 dark:bg-slate-700"
                        }`} />
                    )}
                </div>
            ))}
        </div>
    );

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl p-6">
                    {renderProgress()}
                    {step === 1 && renderStep1()}
                    {step === 2 && renderStep2()}
                    {step === 3 && renderStep3()}
                    {step === 4 && renderStep4()}
                </div>
            </div>
        </div>
    );
}
