"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { PaperTradingTabContainer } from "@/features/dashboard/components/PaperTradingTabContainer";

export default function PaperTradingPage() {
    const { isAuthenticated, loading: authLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!authLoading) {
            if (!isAuthenticated && typeof window !== 'undefined' && !localStorage.getItem("token")) {
                router.push("/login");
            }
        }
    }, [isAuthenticated, authLoading, router]);

    if (authLoading) {
        return (
            <div className="h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                <RefreshCw className="h-8 w-8 text-blue-600 animate-spin" />
            </div>
        );
    }

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col overflow-hidden">
            {/* Header */}
            <header className="flex h-16 items-center px-6 border-b bg-white dark:bg-slate-900 shrink-0 gap-4 z-50">
                <Link href="/" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                    <ArrowLeft className="h-5 w-5 text-slate-500" />
                </Link>
                <div className="flex flex-col">
                    <h1 className="font-black text-lg tracking-tight uppercase">远航模拟测试舱</h1>
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Paper Trading Dashboard</span>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-4 md:p-8">
                <div className="max-w-7xl mx-auto">
                    <PaperTradingTabContainer />
                </div>
            </main>
        </div>
    );
}
