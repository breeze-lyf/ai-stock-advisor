"use client";

import Link from "next/link";
import { Bot, BrainCircuit, Newspaper, Plug, ShieldAlert, Trophy } from "lucide-react";
import { BRAND, FEATURES } from "@/shared/config/features";

const POINTS = [
  {
    icon: <BrainCircuit className="h-5 w-5" />,
    title: "懂你的智能体",
    desc: "记住你的持仓、自选和投资画像（风险偏好、周期、风格、市场），每次回答都基于你的真实情况，而不是泛泛而谈。",
  },
  {
    icon: <Newspaper className="h-5 w-5" />,
    title: "每天主动简报",
    desc: "盘前自动梳理持仓异动、相关新闻与宏观热点，生成今日简报，并推送到钉钉群机器人 / Webhook / Telegram。",
  },
  {
    icon: <Trophy className="h-5 w-5" />,
    title: "每条建议可复盘",
    desc: "买入/卖出/持有建议自动入档，到期按真实行情复盘，命中率与收益一目了然——不靠嘴说，靠战绩说话。",
  },
];

const SHOTS = [
  { src: "/images/landing/agent-home.png", alt: "智能体首页：对话 + 今日简报 + 持仓异动" },
  { src: "/images/landing/review.png", alt: "复盘战绩：命中率与建议列表" },
];

export function Landing() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white"><Bot className="h-5 w-5" /></div>
          <span className="font-bold">{BRAND.name}</span>
        </div>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/login" className="text-neutral-600 hover:text-neutral-900 dark:text-neutral-300">登录</Link>
          <Link href="/register" className="rounded-lg bg-neutral-900 px-3 py-1.5 font-medium text-white dark:bg-white dark:text-neutral-900">免费注册</Link>
        </nav>
      </header>

      <section className="mx-auto max-w-4xl px-6 pb-10 pt-12 text-center">
        <p className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"><Plug className="h-3.5 w-3.5" /> 开源 · 可自托管 · 支持 MCP 接入 Claude / Cursor / 钉钉</p>
        <h1 className="text-4xl font-black tracking-tight sm:text-5xl">你的个人投资智能体</h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-neutral-600 dark:text-neutral-400">{BRAND.tagline}。覆盖 A 股、港股、美股。</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {FEATURES.trial && <Link href="/try" className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-700">免登录试用</Link>}
          <Link href="/register" className="rounded-xl border border-neutral-300 px-6 py-3 font-semibold hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900">注册，建立我的智能体</Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 sm:grid-cols-3">
        {POINTS.map((p) => (
          <div key={p.title} className="rounded-2xl border border-neutral-200 p-6 dark:border-neutral-800">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950">{p.icon}</div>
            <h3 className="font-bold">{p.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">{p.desc}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-6xl space-y-8 px-6 py-14">
        {SHOTS.map((s) => (
          <figure key={s.src} className="overflow-hidden rounded-2xl border border-neutral-200 shadow-xl dark:border-neutral-800">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={s.src} alt={s.alt} className="w-full" loading="lazy" />
            <figcaption className="border-t border-neutral-200 bg-neutral-50 px-4 py-2 text-xs text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900">{s.alt}</figcaption>
          </figure>
        ))}
      </section>

      <footer className="border-t border-neutral-200 py-8 text-center text-xs text-neutral-500 dark:border-neutral-800">
        <p className="flex items-center justify-center gap-1.5"><ShieldAlert className="h-3.5 w-3.5" /> 本产品内容由 AI 基于公开数据生成，仅供研究与学习参考，不构成任何投资建议。投资有风险，决策需独立。</p>
      </footer>
    </div>
  );
}
