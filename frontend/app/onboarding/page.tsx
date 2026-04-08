"use client";

import { Suspense } from "react";
import { OnboardingWizard } from "@/components/features/OnboardingWizard";

function OnboardingContent() {
    return <OnboardingWizard />;
}

export default function OnboardingPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-600 dark:text-slate-400">Loading...</p>
                </div>
            </div>
        }>
            <OnboardingContent />
        </Suspense>
    );
}
