"use client";

import { Suspense } from "react";
import { OnboardingWizard } from "@/components/features/OnboardingWizard";

function OnboardingContent() {
    return <OnboardingWizard />;
}

export default function OnboardingPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-950 flex items-center justify-center">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-neutral-600 dark:text-neutral-400">Loading...</p>
                </div>
            </div>
        }>
            <OnboardingContent />
        </Suspense>
    );
}
