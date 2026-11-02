import { PRICE_COLOR_BOOT_SCRIPT } from "@/shared/theme/priceColorBoot";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "你的个人投资智能体 · Personal Investment Agent",
  description: "记得你的持仓与风格、每天主动简报、每条建议可复盘的开源 AI 投资智能体，支持 MCP 接入 Claude / Cursor / 钉钉。",
};

import { AuthProvider } from "@/context/AuthContext";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" data-updown="green_up" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: PRICE_COLOR_BOOT_SCRIPT }} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
        >
          <AuthProvider>
            <TooltipProvider>
              <ErrorBoundary>
                <main className="flex-1 flex flex-col">
                  {children}
                </main>
              </ErrorBoundary>
            </TooltipProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
