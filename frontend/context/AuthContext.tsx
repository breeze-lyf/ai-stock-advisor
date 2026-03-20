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

const PUBLIC_ROUTES = ["/login", "/register"];

function getApiBaseURL(): string {
    const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
    if (configured) {
        return configured.replace(/\/api\/?$/, "");
    }

    if (typeof window !== "undefined") {
        return window.location.origin.replace(/\/$/, "");
    }

    return "http://localhost:8000";
}

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
            const apiBase = getApiBaseURL();
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

    // Initialize auth state once to avoid route-change flicker.
    useEffect(() => {
        let active = true;

        const initializeAuth = async () => {
            const storedToken = localStorage.getItem("token");
            if (storedToken) {
                setToken(storedToken);
                await refreshProfile();
            }

            if (active) {
                setLoading(false);
            }
        };

        initializeAuth();

        return () => {
            active = false;
        };
    }, []);

    // Handle route guard after initialization; keep loading stable across page switches.
    useEffect(() => {
        if (loading) return;
        if (!token && !PUBLIC_ROUTES.includes(pathname)) {
            router.replace("/login");
        }
    }, [loading, token, pathname, router]);

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
        router.replace("/login");
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
