"use client";

import React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";
import { UserProfile } from "@/types";
import { Settings, LogOut } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import clsx from "clsx";

interface UserMenuProps {
    user: UserProfile;
}

export function UserMenu({ user }: UserMenuProps) {
    const { logout } = useAuth();
    const isPro = user.membership_tier === "PRO";

    const handleLogout = () => {
        logout();
    };

    return (
        <div className="flex items-center gap-3">
            {/* Membership Badge */}
            <div className={clsx(
                "px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-widest uppercase transition-all duration-300 shadow-sm",
                isPro 
                    ? "bg-neutral-900 text-white border border-neutral-700 ring-1 ring-neutral-800" 
                    : "bg-neutral-100 text-neutral-500 border border-neutral-200"
            )}>
                {isPro ? "PRO" : "FREE"}
            </div>

            <div className="flex items-center gap-2">
                <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                        <button className="flex items-center gap-1.5 focus:outline-none group">
                            <div className="relative p-[2px] rounded-full bg-gradient-to-tr from-yellow-400 via-rose-600 to-blue-600 animate-gradient-slow shadow-lg group-hover:scale-105 transition-transform duration-300">
                                <Avatar.Root className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-neutral-100 border-2 border-white dark:border-neutral-900 shadow-inner">
                                    <Avatar.Image
                                        className="h-full w-full object-cover"
                                        src="/images/avatar.png"
                                        alt={user.email}
                                    />
                                    <Avatar.Fallback className="flex h-full w-full items-center justify-center bg-neutral-100 text-sm font-bold text-neutral-500">
                                        {user.email.substring(0, 2).toUpperCase()}
                                    </Avatar.Fallback>
                                </Avatar.Root>
                            </div>
                        </button>
                    </DropdownMenu.Trigger>

                    <DropdownMenu.Portal>
                        <DropdownMenu.Content
                            className="min-w-[200px] overflow-hidden rounded-xl bg-white dark:bg-neutral-900 p-1.5 shadow-2xl ring-1 ring-neutral-200 dark:ring-neutral-800 animate-in fade-in zoom-in-95 duration-200 z-[100]"
                            sideOffset={10}
                            align="end"
                        >
                            <div className="px-3 py-2.5 mb-1.5 border-b border-neutral-100 dark:border-neutral-800">
                                <p className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider mb-0.5">Current Account</p>
                                <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100 truncate">{user.email}</p>
                            </div>

                            <DropdownMenu.Item asChild>
                                <Link href="/settings" className="group flex h-9 items-center gap-2.5 rounded-lg px-2 text-sm font-medium text-neutral-700 outline-none transition-colors hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800">
                                    <Settings className="h-4 w-4 text-neutral-400 group-hover:text-blue-600 transition-colors" />
                                    <span>设置 (Settings)</span>
                                </Link>
                            </DropdownMenu.Item>

                        </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                </DropdownMenu.Root>

                {/* Independent Logout Button */}
                <button 
                    onClick={handleLogout}
                    className="flex h-9 w-9 items-center justify-center rounded-full text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-300"
                    title="退出登录"
                >
                    <LogOut className="h-5 w-5" />
                </button>
            </div>
        </div>
    );
}
