"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "@/context/AuthContext";
import { AuthSplitLayout } from "@/components/auth/AuthSplitLayout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/shared/api/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await api.post("/api/v1/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      const token = response.data.access_token;
      login(token);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthSplitLayout
      mode="login"
      error={error}
      loading={loading}
      onSubmit={handleSubmit}
    >
      {(language, labels, placeholders) => (
        <>
          <div className="space-y-3">
            <Label htmlFor="email" className="text-sm font-medium tracking-wide text-white/78">
              {labels.email}
            </Label>
            <Input
              id="email"
              type="email"
              placeholder={placeholders.email}
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-14 rounded-[1.4rem] border border-white/12 bg-white/[0.08] px-5 text-base text-white shadow-none placeholder:text-white/30 focus-visible:border-emerald-300/40 focus-visible:ring-emerald-200/10"
              aria-label={labels.email}
              data-language={language}
            />
          </div>
          <div className="space-y-3">
            <Label htmlFor="password" className="text-sm font-medium tracking-wide text-white/78">
              {labels.password}
            </Label>
            <Input
              id="password"
              type="password"
              placeholder={placeholders.password}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-14 rounded-[1.4rem] border border-white/12 bg-white/[0.08] px-5 text-base text-white shadow-none placeholder:text-white/30 focus-visible:border-emerald-300/40 focus-visible:ring-emerald-200/10"
              aria-label={labels.password}
              data-language={language}
            />
          </div>
        </>
      )}
    </AuthSplitLayout>
  );
}
