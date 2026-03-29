"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  ArrowRight,
  BarChart3,
  BellRing,
  Brain,
  CandlestickChart,
  Check,
  Command,
  Languages,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type AuthMode = "login" | "register";
type Language = "en" | "zh";

type IconType = typeof Brain;

type Copy = {
  brand: string;
  nav: string[];
  loginLabel: string;
  getStartedLabel: string;
  launchBadge: string;
  heroTitleLine1: string;
  heroTitleLine2: string;
  heroDescription: string;
  heroPrimaryCta: string;
  heroSecondaryCta: string;
  heroTrust: string;
  trustedByTitle: string;
  trustedBy: string[];
  featuresHeading: string;
  featuresDescription: string;
  featureCards: {
    title: string;
    description: string;
    icon: IconType;
    accent?: string;
    stats?: { value: string; label: string }[];
    tags?: string[];
  }[];
  pricingHeading: string;
  pricingDescription: string;
  pricingToggle: { monthly: string; yearly: string; badge: string };
  plans: {
    name: string;
    price: string;
    suffix: string;
    description: string;
    features: string[];
    cta: string;
    highlight?: boolean;
    badge?: string;
  }[];
  finalHeading: string;
  finalDescription: string;
  finalPrimaryCta: string;
  finalSecondaryCta: string;
  footerColumns: { title: string; items: string[] }[];
  footerSummary: string;
  footerTag: string;
  authEyebrow: { login: string; register: string };
  authTabs: { login: string; register: string };
  authTitle: { login: string; register: string };
  authDescription: { login: string; register: string };
  submitLabel: { login: string; register: string };
  loadingLabel: { login: string; register: string };
  fieldLabels: { email: string; password: string };
  fieldPlaceholders: { email: string; password: string };
  switchPrompt: { login: string; register: string };
  switchLabel: { login: string; register: string };
  authFootnote: string;
  languageLabel: string;
  illustrativeNote: string;
};

type AuthSplitLayoutProps = {
  mode: AuthMode;
  error?: string;
  loading?: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  children: (language: Language, labels: Copy["fieldLabels"], placeholders: Copy["fieldPlaceholders"]) => ReactNode;
};

const deferredSectionStyle = {
  contentVisibility: "auto",
  containIntrinsicSize: "1px 900px",
} as const;

const copy: Record<Language, Copy> = {
  en: {
    brand: "AI Smart Investment Advisor",
    nav: ["Features", "Pricing", "Docs", "Blog"],
    loginLabel: "Sign In",
    getStartedLabel: "Get Started",
    launchBadge: "Now in Public Beta",
    heroTitleLine1: "Research faster.",
    heroTitleLine2: "Invest smarter.",
    heroDescription:
      "The modern intelligence platform for investors who move fast. Built to scan markets, explain signals, and turn analysis into portfolio decisions.",
    heroPrimaryCta: "Start Exploring",
    heroSecondaryCta: "View Demo",
    heroTrust: "Trusted by 2,000+ research-heavy investor workflows",
    trustedByTitle: "Trusted by modern research stacks",
    trustedBy: ["Notion", "Figma", "Slack", "Discord", "GitHub"],
    featuresHeading: "Everything you need to move with the market",
    featuresDescription:
      "Built for active investors. Powerful surfaces that help you monitor, analyze, and execute faster than manual workflows ever could.",
    featureCards: [
      {
        title: "Real-time Monitoring",
        description: "Track market health, portfolio drift, and alert streams in one live command surface.",
        icon: BellRing,
        stats: [
          { value: "85%", label: "Signal coverage" },
          { value: "92%", label: "Watchlist clarity" },
          { value: "79%", label: "Macro visibility" },
          { value: "81%", label: "Execution readiness" },
        ],
      },
      {
        title: "Command Palette",
        description: "Navigate everything instantly with a workflow-first control layer and keyboard-friendly actions.",
        icon: Command,
        tags: ["⌘ K", "AI Search", "Quick Actions"],
      },
      {
        title: "Deep Analytics",
        description: "Compress technical, news, and portfolio context into readable investment briefs.",
        icon: BarChart3,
        accent: "+32% decision speed",
      },
      {
        title: "Blazing Fast",
        description: "Designed for rapid scan-review-act loops so market context stays warm while decisions are made.",
        icon: TrendingUp,
        accent: "<30s avg review cycle",
      },
      {
        title: "Enterprise Security",
        description: "SOC-inspired access patterns, encrypted credentials, and separated portfolio operations.",
        icon: ShieldCheck,
        tags: ["Access control", "Audit logs", "Encrypted keys"],
      },
    ],
    pricingHeading: "Simple, transparent pricing",
    pricingDescription: "Start free, scale as your workflow expands. No hidden steps, no complicated packaging.",
    pricingToggle: { monthly: "Monthly", yearly: "Yearly", badge: "-20%" },
    plans: [
      {
        name: "Starter",
        price: "$0",
        suffix: "",
        description: "Perfect for solo investors and lightweight research.",
        features: ["3 watchlists", "10 portfolio positions", "Basic AI analysis", "Community support", "1 GB storage"],
        cta: "Get Started",
      },
      {
        name: "Pro",
        price: "$29",
        suffix: "/month",
        description: "For growing investors who need more depth and speed.",
        features: ["Unlimited watchlists", "Unlimited projects", "Advanced analytics", "Priority support", "10 GB storage", "API access"],
        cta: "Start Free Trial",
        highlight: true,
        badge: "Most Popular",
      },
      {
        name: "Enterprise",
        price: "$99",
        suffix: "/month",
        description: "For teams with governance, scale, and custom integration needs.",
        features: ["Everything in Pro", "SSO & SAML", "Dedicated support", "SLA guarantee", "Unlimited storage", "Custom workflows"],
        cta: "Contact Sales",
      },
    ],
    finalHeading: "Ready to invest with more context?",
    finalDescription:
      "Join teams and individual investors already using one workspace for scanning, analysis, and execution. Start free with no credit card required.",
    finalPrimaryCta: "Get Started for Free",
    finalSecondaryCta: "Talk to Sales",
    footerColumns: [
      { title: "Product", items: ["Features", "Pricing", "Changelog", "Roadmap", "API"] },
      { title: "Resources", items: ["Documentation", "Guides", "Blog", "Community", "Templates"] },
      { title: "Company", items: ["About", "Careers", "Press", "Partners", "Contact"] },
      { title: "Legal", items: ["Privacy", "Terms", "Security", "Cookies", "Licenses"] },
    ],
    footerSummary: "The modern platform for investors who want signal, context, and action in one place.",
    footerTag: "AI System Operational",
    authEyebrow: { login: "Access Workspace", register: "Start Free" },
    authTabs: { login: "Login", register: "Register" },
    authTitle: { login: "Continue your session", register: "Create your account" },
    authDescription: {
      login: "Sign in to resume research, alerts, and portfolio workflows.",
      register: "Open your workspace for AI analysis, monitoring, and trading operations.",
    },
    submitLabel: { login: "Login", register: "Create Account" },
    loadingLabel: { login: "Logging in...", register: "Creating account..." },
    fieldLabels: { email: "Email", password: "Password" },
    fieldPlaceholders: { email: "name@company.com", password: "Enter your password" },
    switchPrompt: { login: "New here?", register: "Already have an account?" },
    switchLabel: { login: "Create an account", register: "Sign in" },
    authFootnote: "Illustrative metrics and customer counts on this page are marketing placeholders until replaced with measured data.",
    languageLabel: "中文",
    illustrativeNote: "Illustrative marketing numbers",
  },
  zh: {
    brand: "AI 智能投顾助手",
    nav: ["功能", "价格", "文档", "博客"],
    loginLabel: "登录",
    getStartedLabel: "立即开始",
    launchBadge: "公开测试中",
    heroTitleLine1: "研究更快。",
    heroTitleLine2: "投资更聪明。",
    heroDescription:
      "面向高频研究型投资者的现代智能平台。帮助你扫描市场、解释信号，并把分析快速转成投资组合决策。",
    heroPrimaryCta: "开始探索",
    heroSecondaryCta: "查看演示",
    heroTrust: "已支持 2,000+ 重研究流程的投资工作流",
    trustedByTitle: "受到现代研究型团队青睐",
    trustedBy: ["Notion", "Figma", "Slack", "Discord", "GitHub"],
    featuresHeading: "你需要的一切，都在同一个市场工作台里",
    featuresDescription:
      "为主动型投资者设计。让监控、分析、理解和执行比人工切换页面更快、更连贯。",
    featureCards: [
      {
        title: "实时监控",
        description: "把市场健康度、持仓偏移和预警流整合到一个实时指挥面板里。",
        icon: BellRing,
        stats: [
          { value: "85%", label: "信号覆盖" },
          { value: "92%", label: "自选股清晰度" },
          { value: "79%", label: "宏观可见性" },
          { value: "81%", label: "执行准备度" },
        ],
      },
      {
        title: "命令面板",
        description: "通过工作流导向的控制层与键盘快捷操作，快速抵达任何功能。",
        icon: Command,
        tags: ["⌘ K", "AI 搜索", "快捷动作"],
      },
      {
        title: "深度分析",
        description: "把技术面、新闻与持仓背景压缩成可阅读的投资摘要。",
        icon: BarChart3,
        accent: "+32% 决策速度",
      },
      {
        title: "极速工作流",
        description: "围绕快速扫描、快速判断、快速执行设计，让上下文始终保持热状态。",
        icon: TrendingUp,
        accent: "<30 秒平均复盘周期",
      },
      {
        title: "企业级安全",
        description: "借鉴企业级访问控制和加密方式，保护凭证、持仓和策略操作。",
        icon: ShieldCheck,
        tags: ["访问控制", "审计日志", "密钥加密"],
      },
    ],
    pricingHeading: "简单透明的价格",
    pricingDescription: "先免费开始，随着你的研究和交易流程扩展再升级，没有复杂套餐。",
    pricingToggle: { monthly: "月付", yearly: "年付", badge: "-20%" },
    plans: [
      {
        name: "Starter",
        price: "$0",
        suffix: "",
        description: "适合个人投资者和轻量研究场景。",
        features: ["3 个自选列表", "10 个持仓席位", "基础 AI 分析", "社区支持", "1 GB 存储"],
        cta: "立即开始",
      },
      {
        name: "Pro",
        price: "$29",
        suffix: "/月",
        description: "适合需要更高深度与速度的进阶用户。",
        features: ["无限自选列表", "无限项目", "高级分析", "优先支持", "10 GB 存储", "API 访问"],
        cta: "开始免费试用",
        highlight: true,
        badge: "最受欢迎",
      },
      {
        name: "Enterprise",
        price: "$99",
        suffix: "/月",
        description: "适合团队治理、规模协作和自定义集成需求。",
        features: ["包含 Pro 全部功能", "SSO & SAML", "专属支持", "SLA 保证", "无限存储", "自定义流程"],
        cta: "联系销售",
      },
    ],
    finalHeading: "准备好用更多上下文做投资判断了吗？",
    finalDescription:
      "加入已经用同一工作台完成扫描、分析和执行的团队与个人投资者。免费开始，无需信用卡。",
    finalPrimaryCta: "免费开始",
    finalSecondaryCta: "联系销售",
    footerColumns: [
      { title: "产品", items: ["功能", "价格", "更新日志", "路线图", "API"] },
      { title: "资源", items: ["文档", "指南", "博客", "社区", "模板"] },
      { title: "公司", items: ["关于", "招聘", "媒体", "合作伙伴", "联系"] },
      { title: "法律", items: ["隐私", "条款", "安全", "Cookies", "许可"] },
    ],
    footerSummary: "为希望在一个地方完成信号获取、上下文理解和动作执行的投资者而设计。",
    footerTag: "AI 系统运行中",
    authEyebrow: { login: "进入工作台", register: "免费开始" },
    authTabs: { login: "登录", register: "注册" },
    authTitle: { login: "继续你的研究流程", register: "创建你的账号" },
    authDescription: {
      login: "登录后继续查看研究、预警和投资组合工作流。",
      register: "注册后即可开启 AI 分析、市场监控和交易操作台。",
    },
    submitLabel: { login: "登录", register: "创建账号" },
    loadingLabel: { login: "登录中...", register: "注册中..." },
    fieldLabels: { email: "邮箱", password: "密码" },
    fieldPlaceholders: { email: "name@company.com", password: "请输入密码" },
    switchPrompt: { login: "第一次使用？", register: "已经有账号？" },
    switchLabel: { login: "立即注册", register: "去登录" },
    authFootnote: "本页中的示例指标和用户规模属于营销占位数据，后续应替换为真实可验证数据。",
    languageLabel: "EN",
    illustrativeNote: "示例营销数据",
  },
};

function getStoredLanguage(): Language {
  if (typeof window === "undefined") return "zh";
  const value = window.localStorage.getItem("marketing-language");
  return value === "en" || value === "zh" ? value : "zh";
}

export function AuthSplitLayout({
  mode,
  error,
  loading = false,
  onSubmit,
  children,
}: AuthSplitLayoutProps) {
  const [language, setLanguage] = useState<Language>(() => getStoredLanguage());
  const t = copy[language];
  const isLogin = mode === "login";

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("marketing-language", language);
    }
  }, [language]);

  return (
    <div className="min-h-screen bg-[#050507] text-white">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.14),_rgba(255,255,255,0)_30%)]" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[44rem] bg-[linear-gradient(180deg,_rgba(255,255,255,0.06)_0%,_rgba(5,5,7,0)_65%)]" />
        <div className="pointer-events-none absolute left-1/2 top-28 h-72 w-[34rem] -translate-x-1/2 rounded-full bg-white/4 blur-2xl" />

        <div className="relative mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <header className="fixed inset-x-0 top-4 z-50 mx-auto flex w-[min(100%-1.5rem,72rem)] items-center justify-between gap-4 rounded-full border border-white/12 bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.03))] px-3 py-3 shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_16px_40px_rgba(0,0,0,0.36)] backdrop-blur-md supports-[backdrop-filter]:bg-black/24 sm:w-[min(100%-3rem,72rem)]">
            <div className="flex items-center gap-3 pl-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-black">
                <CandlestickChart className="h-4 w-4" />
              </span>
              <span className="text-sm font-medium text-white">{t.brand}</span>
            </div>

            <nav className="hidden items-center gap-6 text-sm text-white/60 md:flex">
              {t.nav.map((item) => (
                <span key={item} className="transition hover:text-white">
                  {item}
                </span>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                className="rounded-full px-4 text-white/75 hover:bg-white/8 hover:text-white"
                onClick={() => setLanguage((current) => (current === "zh" ? "en" : "zh"))}
              >
                <Languages className="h-4 w-4" />
                {t.languageLabel}
              </Button>
              <Link
                href={isLogin ? "/login" : "/login"}
                className="hidden rounded-full px-4 py-2 text-sm text-white/75 transition hover:text-white md:inline-flex"
              >
                {t.loginLabel}
              </Link>
              <Link
                href={isLogin ? "/register" : "/register"}
                className="inline-flex rounded-full bg-white px-5 py-2.5 text-sm font-medium text-black transition hover:bg-white/90"
              >
                {t.getStartedLabel}
              </Link>
            </div>
          </header>

          <section className="grid gap-10 px-2 pb-18 pt-28 lg:grid-cols-[minmax(0,1fr)_26rem] lg:items-start lg:pt-36">
            <div className="pt-6 lg:pt-10">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white/70">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.8)]" />
                {t.launchBadge}
              </div>

              <h1 className="mt-8 text-5xl font-semibold leading-none tracking-[-0.06em] text-white sm:text-6xl lg:text-[5.8rem]">
                <span className="block">{t.heroTitleLine1}</span>
                <span className="block text-white/45">{t.heroTitleLine2}</span>
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-8 text-white/62">
                {t.heroDescription}
              </p>

              <div className="mt-10 flex flex-wrap gap-4">
                <Link
                  href={isLogin ? "/register" : "/register"}
                  className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3.5 text-sm font-medium text-black transition hover:bg-white/92"
                >
                  {t.heroPrimaryCta}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.03] px-6 py-3.5 text-sm font-medium text-white/80 transition hover:bg-white/[0.06]"
                >
                  {t.heroSecondaryCta}
                </button>
              </div>

              <div className="mt-12">
                <div className="flex -space-x-3">
                  {[0, 1, 2, 3, 4].map((item) => (
                    <div
                      key={item}
                      className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[#050507] bg-gradient-to-br from-slate-200 to-slate-400 text-xs font-semibold text-black"
                    >
                      {String.fromCharCode(65 + item)}
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-sm text-white/45">{t.heroTrust}</p>
              </div>
            </div>

            <div className="lg:sticky lg:top-8">
              <Card className="rounded-[2rem] border border-white/12 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] py-0 text-white shadow-[0_20px_56px_rgba(0,0,0,0.38)] backdrop-blur-xl supports-[backdrop-filter]:bg-black/22">
                <CardHeader className="border-b border-white/10 px-7 py-7">
                  <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
                    {t.authEyebrow[mode]}
                  </div>

                  <div className="mb-5 grid grid-cols-2 gap-2 rounded-[20px] border border-white/8 bg-white/[0.04] p-1 backdrop-blur-sm">
                    <Link
                      href="/login"
                      className={`rounded-[16px] px-4 py-3 text-center text-sm font-medium transition ${
                        isLogin ? "bg-white text-black" : "text-white/55 hover:text-white"
                      }`}
                    >
                      {t.authTabs.login}
                    </Link>
                    <Link
                      href="/register"
                      className={`rounded-[16px] px-4 py-3 text-center text-sm font-medium transition ${
                        !isLogin ? "bg-white text-black" : "text-white/55 hover:text-white"
                      }`}
                    >
                      {t.authTabs.register}
                    </Link>
                  </div>

                  <CardTitle className="text-3xl font-semibold tracking-[-0.04em] text-white">
                    {t.authTitle[mode]}
                  </CardTitle>
                  <CardDescription className="text-sm leading-6 text-white/55">
                    {t.authDescription[mode]}
                  </CardDescription>
                </CardHeader>

                <form onSubmit={onSubmit}>
                  <CardContent className="space-y-5 px-7 py-7">
                    {error ? (
                      <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200 backdrop-blur-sm">
                        {error}
                      </div>
                    ) : null}

                    {children(language, t.fieldLabels, t.fieldPlaceholders)}

                    <Button
                      className="h-12 w-full rounded-full bg-white text-sm font-semibold text-black hover:bg-white/92"
                      type="submit"
                      disabled={loading}
                    >
                      {loading ? t.loadingLabel[mode] : t.submitLabel[mode]}
                      {!loading ? <ArrowRight className="h-4 w-4" /> : null}
                    </Button>
                  </CardContent>

                  <CardFooter className="flex-col items-start gap-3 border-t border-white/10 px-7 py-6">
                    <div className="text-sm text-white/60">
                      {t.switchPrompt[mode]}{" "}
                      <Link href={isLogin ? "/register" : "/login"} className="font-medium text-white underline underline-offset-4">
                        {t.switchLabel[mode]}
                      </Link>
                    </div>
                    <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] text-white/45 backdrop-blur-sm">
                      <Sparkles className="h-3.5 w-3.5" />
                      {t.illustrativeNote}
                    </div>
                    <p className="text-xs leading-5 text-white/35">{t.authFootnote}</p>
                  </CardFooter>
                </form>
              </Card>
            </div>
          </section>

          <section className="border-t border-white/6 py-10" style={deferredSectionStyle}>
            <div className="text-center text-xs font-medium uppercase tracking-[0.28em] text-white/30">
              {t.trustedByTitle}
            </div>
            <div className="mt-8 grid grid-cols-2 gap-6 text-center text-white/38 sm:grid-cols-3 lg:grid-cols-5">
              {t.trustedBy.map((item) => (
                <div key={item} className="flex items-center justify-center gap-3 rounded-full border border-white/6 bg-white/[0.02] px-5 py-4">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/[0.05] text-xs">{item[0]}</span>
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="py-20" style={deferredSectionStyle}>
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl">
                {t.featuresHeading}
              </h2>
              <p className="mt-5 text-base leading-7 text-white/50">{t.featuresDescription}</p>
            </div>

            <div className="mt-14 grid gap-4 lg:grid-cols-3">
              <div className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-6 lg:col-span-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.05] text-white">
                      <BellRing className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-2xl font-semibold">{t.featureCards[0].title}</h3>
                    <p className="mt-2 max-w-xl text-sm leading-7 text-white/55">{t.featureCards[0].description}</p>
                  </div>
                  <div className="hidden items-center gap-2 lg:flex">
                    {[0, 1, 2, 3].map((item) => (
                      <span key={item} className={`h-2.5 w-2.5 rounded-full ${item === 0 ? "bg-emerald-400" : "bg-white/18"}`} />
                    ))}
                  </div>
                </div>

                <div className="mt-10 grid gap-6 sm:grid-cols-4">
                  {t.featureCards[0].stats?.map((item) => (
                    <div key={item.label}>
                      <div className="text-3xl font-semibold tracking-[-0.04em] text-white">{item.value}</div>
                      <div className="mt-2 text-sm text-white/40">{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-6">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.05] text-white">
                  <Command className="h-5 w-5" />
                </div>
                <h3 className="mt-5 text-2xl font-semibold">{t.featureCards[1].title}</h3>
                <p className="mt-2 text-sm leading-7 text-white/55">{t.featureCards[1].description}</p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {t.featureCards[1].tags?.map((tag) => (
                    <span key={tag} className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/60">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {t.featureCards.slice(2).map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.title} className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-6">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.05] text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-2xl font-semibold">{item.title}</h3>
                    <p className="mt-2 text-sm leading-7 text-white/55">{item.description}</p>
                    {item.accent ? <div className="mt-6 text-sm font-medium text-emerald-300">{item.accent}</div> : null}
                    {item.tags ? (
                      <div className="mt-6 flex flex-wrap gap-2">
                        {item.tags.map((tag) => (
                          <span key={tag} className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/60">
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="py-16" style={deferredSectionStyle}>
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl">
                {t.pricingHeading}
              </h2>
              <p className="mt-5 text-base leading-7 text-white/50">{t.pricingDescription}</p>
              <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] p-1 text-sm text-white/70">
                <span className="rounded-full bg-white/[0.07] px-4 py-2">{t.pricingToggle.monthly}</span>
                <span className="px-3 py-2">{t.pricingToggle.yearly}</span>
                <span className="rounded-full bg-emerald-400/15 px-3 py-2 text-emerald-300">{t.pricingToggle.badge}</span>
              </div>
            </div>

            <div className="mt-14 grid items-stretch gap-5 lg:grid-cols-3 lg:[grid-auto-rows:1fr]">
              {t.plans.map((plan) => (
                <div
                  key={plan.name}
                  className={`relative flex h-full flex-col rounded-[2rem] border p-6 ${
                    plan.highlight
                      ? "border-white/16 bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.03))] shadow-[0_24px_80px_rgba(255,255,255,0.06)]"
                      : "border-white/10 bg-white/[0.03]"
                  }`}
                >
                  {plan.badge ? (
                    <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold text-black">
                      {plan.badge}
                    </div>
                  ) : null}
                  <h3 className="text-2xl font-semibold text-white">{plan.name}</h3>
                  <p className="mt-2 text-sm text-white/45">{plan.description}</p>
                  <div className="mt-6 flex items-end gap-1">
                    <span className="text-5xl font-semibold tracking-[-0.05em] text-white">{plan.price}</span>
                    <span className="pb-1 text-sm text-white/45">{plan.suffix}</span>
                  </div>
                  <div className="mt-8 space-y-3">
                    {plan.features.map((feature) => (
                      <div key={feature} className="flex items-center gap-3 text-sm text-white/70">
                        <Check className="h-4 w-4 text-emerald-300" />
                        {feature}
                      </div>
                    ))}
                  </div>
                  <div className="mt-auto pt-8">
                    <button
                      type="button"
                      className={`inline-flex w-full items-center justify-center rounded-full px-4 py-3 text-sm font-medium transition ${
                        plan.highlight
                          ? "bg-white text-black hover:bg-white/92"
                          : "border border-white/10 bg-white/[0.04] text-white hover:bg-white/[0.07]"
                      }`}
                    >
                      {plan.cta}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="py-24 text-center" style={deferredSectionStyle}>
            <h2 className="text-5xl font-semibold tracking-[-0.06em] text-white sm:text-6xl">
              {t.finalHeading}
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-white/50">
              {t.finalDescription}
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              <Link
                href={isLogin ? "/register" : "/register"}
                className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3.5 text-sm font-medium text-black transition hover:bg-white/92"
              >
                {t.finalPrimaryCta}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.03] px-6 py-3.5 text-sm font-medium text-white/80 transition hover:bg-white/[0.06]"
              >
                {t.finalSecondaryCta}
              </button>
            </div>
          </section>

          <footer className="border-t border-white/8 py-10" style={deferredSectionStyle}>
            <div className="grid gap-10 lg:grid-cols-[1.2fr_repeat(4,1fr)]">
              <div>
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-black">
                    <CandlestickChart className="h-4 w-4" />
                  </span>
                  <span className="font-medium text-white">{t.brand}</span>
                </div>
                <p className="mt-4 max-w-xs text-sm leading-7 text-white/45">{t.footerSummary}</p>
                <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/55">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
                  {t.footerTag}
                </div>
              </div>

              {t.footerColumns.map((column) => (
                <div key={column.title}>
                  <h3 className="text-sm font-medium text-white">{column.title}</h3>
                  <div className="mt-4 space-y-3">
                    {column.items.map((item) => (
                      <div key={item} className="text-sm text-white/45 transition hover:text-white/80">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
