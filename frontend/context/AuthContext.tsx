"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

import { UserProfile } from "@/types";

interface AuthContextType {
    token: string | null;
    user: UserProfile | null;
    loading: boolean;
    login: (token: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
    refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_ROUTES = ["/login", "/register", "/password"];

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    const refreshProfile = async () => {
        const storedToken = localStorage.getItem("token");
        if (!storedToken) return;
        
        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiBase}/api/v1/user/me`, {
                headers: { "Authorization": `Bearer ${storedToken}` }
            });
            if (response.ok) {
                const data = await response.json();
                setUser(data);
            } else if (response.status === 401 || response.status === 403) {
                localStorage.removeItem("token");
                setToken(null);
                setUser(null);
            }
        } catch (error) {
            console.error("Failed to refresh profile", error);
        }
    };

    useEffect(() => {
        let active = true;

        const initializeAuth = async () => {
            const storedToken = localStorage.getItem("token");
            if (storedToken) {
                setToken(storedToken);
                await refreshProfile();
            } else if (!PUBLIC_ROUTES.includes(pathname)) {
                router.push("/login");
            }

            if (active) {
                setLoading(false);
            }
        };

        setLoading(true);
        initializeAuth();

        return () => {
            active = false;
        };
    }, [pathname, router]);

    const login = (newToken: string) => {
        localStorage.setItem("token", newToken);
        setToken(newToken);
        setLoading(false);
        router.push("/");
    };

    const logout = () => {
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
        setLoading(false);
        router.push("/login");
    };

    return (
        <AuthContext.Provider
            value={{
                token,
                user,
                loading,
                login,
                logout,
                isAuthenticated: !!token,
                refreshProfile
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
