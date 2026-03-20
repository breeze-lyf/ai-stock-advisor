"use client";

import React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";
import { UserProfile } from "@/types";
import { Settings, LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import clsx from "clsx";

interface UserMenuProps {
    user: UserProfile;
}

export function UserMenu({ user }: UserMenuProps) {
    const router = useRouter();
    const isPro = user.membership_tier === "PRO";

    const handleLogout = () => {
        localStorage.removeItem("token");
        router.push("/login");
    };

    return (
        <div className="flex items-center gap-3">
            {/* Membership Badge */}
            <div className={clsx(
                "px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-widest uppercase transition-all duration-300 shadow-sm",
                isPro 
                    ? "bg-slate-900 text-white border border-slate-700 ring-1 ring-slate-800" 
                    : "bg-slate-100 text-slate-500 border border-slate-200"
            )}>
                {isPro ? "PRO" : "FREE"}
            </div>

            <div className="flex items-center gap-2">
                <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                        <button className="flex items-center gap-1.5 focus:outline-none group">
                            <div className="relative p-[2px] rounded-full bg-gradient-to-tr from-yellow-400 via-rose-600 to-blue-600 animate-gradient-slow shadow-lg group-hover:scale-105 transition-transform duration-300">
                                <Avatar.Root className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-slate-100 border-2 border-white dark:border-slate-900 shadow-inner">
                                    <Avatar.Image
                                        className="h-full w-full object-cover"
                                        src="/images/avatar.png"
                                        alt={user.email}
                                    />
                                    <Avatar.Fallback className="flex h-full w-full items-center justify-center bg-slate-100 text-sm font-bold text-slate-500">
                                        {user.email.substring(0, 2).toUpperCase()}
                                    </Avatar.Fallback>
                                </Avatar.Root>
                            </div>
                        </button>
                    </DropdownMenu.Trigger>

                    <DropdownMenu.Portal>
                        <DropdownMenu.Content
                            className="min-w-[200px] overflow-hidden rounded-xl bg-white dark:bg-slate-900 p-1.5 shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in fade-in zoom-in-95 duration-200 z-[100]"
                            sideOffset={10}
                            align="end"
                        >
                            <div className="px-3 py-2.5 mb-1.5 border-b border-slate-100 dark:border-slate-800">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Current Account</p>
                                <p className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{user.email}</p>
                            </div>

                            <DropdownMenu.Item className="group flex h-9 items-center px-2 text-sm font-medium text-slate-700 dark:text-slate-300 outline-none hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer">
                                <Link href="/settings" className="flex items-center w-full gap-2.5">
                                    <Settings className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
                                    <span>设置 (Settings)</span>
                                </Link>
                            </DropdownMenu.Item>

                        </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                </DropdownMenu.Root>

                {/* Independent Logout Button */}
                <button 
                    onClick={handleLogout}
                    className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-300"
                    title="退出登录"
                >
                    <LogOut className="h-5 w-5" />
                </button>
            </div>
        </div>
    );
}
