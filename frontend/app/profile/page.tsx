"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getProfile } from "@/lib/api";
import { UserProfile } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ArrowLeft, User, Mail, Shield, Calendar, Award } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";

export default function ProfilePage() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const profile = await getProfile();
                setUser(profile);
            } catch (err) {
                console.error("Failed to fetch profile", err);
            } finally {
                setLoading(false);
            }
        };
        fetchUser();
    }, []);

    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 gap-4">
                <p className="text-slate-500">无法加载个人信息</p>
                <Button onClick={() => router.push("/")}>返回首页</Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8 lg:p-12">
            <div className="max-w-2xl mx-auto">
                <Link href="/" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors mb-8 group">
                    <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                    <span className="text-sm font-medium">返回仪表盘</span>
                </Link>

                <div className="space-y-6">
                    <div className="flex flex-col gap-2">
                        <h1 className="text-3xl font-black text-slate-900 dark:text-slate-100 tracking-tight">个人信息</h1>
                        <p className="text-slate-500">管理您的账户详情与会员状态</p>
                    </div>

                    <Card className="border-none shadow-2xl shadow-slate-200/50 dark:shadow-none bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl rounded-2xl overflow-hidden">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <User className="h-5 w-5 text-blue-500" />
                                账户详情
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                                        <Mail className="h-3 w-3" />
                                        电子邮箱
                                    </label>
                                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800">
                                        {user.email}
                                    </p>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                                        <Award className="h-3 w-3" />
                                        会员等级
                                    </label>
                                    <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800">
                                        <span className={clsx(
                                            "px-2 py-0.5 rounded-full text-[10px] font-black tracking-widest uppercase",
                                            user.membership_tier === "PRO" 
                                                ? "bg-slate-900 text-white" 
                                                : "bg-slate-200 text-slate-600"
                                        )}>
                                            {user.membership_tier}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-6 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                                <div className="space-y-1 flex flex-col">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                                        <Shield className="h-3 w-3" />
                                        账户安全
                                    </span>
                                    <span className="text-xs text-slate-500">建议定期更改您的登录密码</span>
                                </div>
                                <Button 
                                    variant="outline" 
                                    className="rounded-xl border-slate-200 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 transition-all font-bold text-xs"
                                    onClick={() => router.push("/password")}
                                >
                                    修改登录密码
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-none shadow-xl shadow-slate-200/50 dark:shadow-none bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm rounded-2xl">
                        <CardContent className="p-6 flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="h-12 w-12 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                                    <Calendar className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">注册时间</p>
                                    <p className="text-xs text-slate-500">您是我们宝贵社区的一员</p>
                                </div>
                            </div>
                            <p className="text-sm font-mono font-bold text-slate-700 dark:text-slate-300">
                                {format(new Date(), "yyyy年MM月dd日", { locale: zhCN })}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}

function clsx(...classes: any[]) {
    return classes.filter(Boolean).join(" ");
}
