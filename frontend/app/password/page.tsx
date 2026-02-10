"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { changePassword } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Key, ShieldCheck, AlertCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export default function PasswordPage() {
    const router = useRouter();
    const [form, setForm] = useState({
        old_password: "",
        new_password: "",
        confirm_password: ""
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (form.new_password !== form.confirm_password) {
            setError("两次输入的新密码不一致");
            return;
        }

        if (form.new_password.length < 6) {
            setError("新密码长度至少为 6 位");
            return;
        }

        setLoading(true);
        try {
            await changePassword({
                old_password: form.old_password,
                new_password: form.new_password
            });
            setSuccess(true);
            setTimeout(() => {
                router.push("/profile");
            }, 2000);
        } catch (err: any) {
            setError(err.response?.data?.detail || "更新失败，请检查旧密码是否正确");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 md:p-8 lg:p-12">
            <div className="max-w-md mx-auto">
                <Link href="/profile" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors mb-8 group">
                    <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                    <span className="text-sm font-medium">返回个人信息</span>
                </Link>

                <Card className="border-none shadow-2xl shadow-slate-200/50 dark:shadow-none bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl rounded-2xl">
                    <CardHeader className="text-center pb-2">
                        <div className="mx-auto h-12 w-12 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mb-4">
                            <Key className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                        </div>
                        <CardTitle className="text-2xl font-black text-slate-900 dark:text-slate-100">修改密码</CardTitle>
                        <CardDescription>为了保障账户安全，请定期更换密码</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {success ? (
                            <div className="py-6 flex flex-col items-center gap-4 animate-in fade-in zoom-in duration-300">
                                <div className="h-16 w-16 rounded-full bg-green-50 dark:bg-green-900/20 flex items-center justify-center">
                                    <CheckCircle2 className="h-10 w-10 text-green-500" />
                                </div>
                                <p className="text-sm font-bold text-green-600">密码修改成功！</p>
                                <p className="text-xs text-slate-400">正在为您跳转...</p>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-5 py-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">当前旧密码</label>
                                    <Input
                                        type="password"
                                        required
                                        className="h-11 rounded-xl bg-slate-50/50 border-slate-100 focus:border-blue-400 transition-all px-4"
                                        placeholder="请输入当前密码"
                                        value={form.old_password}
                                        onChange={(e) => setForm({ ...form, old_password: e.target.value })}
                                    />
                                </div>
                                
                                <div className="h-px bg-slate-100 dark:bg-slate-800 my-2" />

                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">设置新密码</label>
                                    <Input
                                        type="password"
                                        required
                                        className="h-11 rounded-xl bg-slate-50/50 border-slate-100 focus:border-blue-400 transition-all px-4"
                                        placeholder="至少 6 位字符"
                                        value={form.new_password}
                                        onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                                    />
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">重复新密码</label>
                                    <Input
                                        type="password"
                                        required
                                        className="h-11 rounded-xl bg-slate-50/50 border-slate-100 focus:border-blue-400 transition-all px-4"
                                        placeholder="确认新密码"
                                        value={form.confirm_password}
                                        onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                                    />
                                </div>

                                {error && (
                                    <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 text-red-500 text-xs font-bold animate-in slide-in-from-top-1">
                                        <AlertCircle className="h-4 w-4 shrink-0" />
                                        <span>{error}</span>
                                    </div>
                                ) }

                                <Button 
                                    className="w-full h-11 rounded-xl bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/20 font-bold transition-all mt-4"
                                    disabled={loading}
                                >
                                    {loading ? "正在处理..." : "确认修改密码"}
                                </Button>
                            </form>
                        )}
                    </CardContent>
                </Card>

                <div className="mt-8 flex flex-col items-center gap-4">
                    <div className="flex items-center gap-1.5 text-slate-400">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        <span className="text-[10px] font-bold uppercase tracking-widest">Secure Bank-Level Encryption</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
