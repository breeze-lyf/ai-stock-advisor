"use client";

import Link from "next/link";
import { ArrowRight, BrainCircuit, Check, Github, Newspaper, Plug, ShieldAlert, Trophy } from "lucide-react";
import { BRAND, FEATURES } from "@/shared/config/features";
import { BrandMark } from "@/components/features/DashboardHeader";

const REPO = "https://github.com/breeze-lyf/ai-stock-advisor";

const VALUES = [
  {
    icon: BrainCircuit,
    kicker: "懂你",
    title: "记住你的持仓与投资画像",
    desc: "风险偏好、持有周期、投资风格、关注市场，加上你的持仓与自选，都会作为智能体的长期记忆。同一个问题，保守型和积极型投资者会得到不同的回答。",
    points: ["注册引导 1 分钟完成画像", "持仓 / 自选自动注入上下文", "随时在设置中修改"],
    img: "/images/landing/settings-profile.png",
    alt: "投资画像设置",
  },
  {
    icon: Newspaper,
    kicker: "主动",
    title: "每天一份为你写的简报",
    desc: "盘前自动梳理持仓涨跌、相关新闻、宏观热点与需要关注的风险，生成今日简报，并推送到钉钉群机器人、Webhook 或 Telegram。",
    points: ["只针对你的持仓与自选", "钉钉加签机器人 / Webhook / Telegram", "定时任务默认关闭，可一键开启"],
    img: "/images/landing/briefs.png",
    alt: "每日简报",
  },
  {
    icon: Trophy,
    kicker: "可验证",
    title: "每条建议都要被复盘",
    desc: "智能体给出的买入、卖出、持有建议会连同当时价格、周期和理由自动入档，到期按真实行情复盘打分。命中与否，一目了然。",
    points: ["对话、个股诊断、简报统一入档", "到期自动按收盘价评估", "命中率与方向收益公开可查"],
    img: "/images/landing/review.png",
    alt: "复盘战绩",
  },
];

const MCP_JSON = `{
  "mcpServers": {
    "investment-agent": {
      "url": "https://your-domain.com/mcp",
      "headers": {
        "Authorization": "Bearer asa_xxx"
      }
    }
  }
}`;

const TOOLS = ["get_quote", "get_kline_and_technicals", "get_fundamentals", "search_news", "macro_snapshot", "get_portfolio", "run_stock_diagnosis", "ask_stock_agent"];

function Frame({ src, alt, className }: { src: string; alt: string; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-xl border border-white/10 bg-[#0e0f13] shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)] ${className ?? ""}`}>
      <div className="flex h-8 items-center gap-1.5 border-b border-white/[0.06] bg-white/[0.02] px-3">
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
        <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="block w-full" loading="lazy" />
    </div>
  );
}

export function Landing() {
  return (
    <div className="dark min-h-screen bg-[#08090b] text-ink antialiased">
      {/* nav */}
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[#08090b]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <Link href="/" className="flex items-center gap-2.5">
            <BrandMark className="h-7 w-7 rounded-lg" />
            <span className="text-[14px] font-semibold tracking-tight">{BRAND.name}</span>
          </Link>
          <nav className="hidden items-center gap-7 text-[13px] text-ink-3 md:flex">
            <a href="#features" className="hover:text-ink">功能</a>
            <a href="#mcp" className="hover:text-ink">MCP 接入</a>
            <a href={REPO} target="_blank" rel="noreferrer" className="hover:text-ink">GitHub</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login" className="h-8 rounded-lg px-3 text-[13px] leading-8 text-ink-2 hover:text-ink">登录</Link>
            <Link href="/register" className="h-8 rounded-lg bg-white px-3 text-[13px] font-medium leading-8 text-black hover:bg-white/90">免费注册</Link>
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 [background:radial-gradient(60%_50%_at_50%_0%,oklch(0.45_0.16_268/0.35),transparent_70%)]" />
        <div className="pointer-events-none absolute inset-0 opacity-[0.25] [background-image:linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(70%_60%_at_50%_0%,black,transparent)]" />
        <div className="relative mx-auto max-w-6xl px-5 pb-8 pt-20 text-center sm:pt-28">
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] py-1 pl-1 pr-3 text-[12px] text-ink-2 hover:border-white/20">
            <span className="rounded-full bg-brand/20 px-2 py-0.5 text-[11px] font-medium text-brand">开源</span>
            可自托管 · 支持 MCP 接入 Claude / Cursor / 钉钉
            <ArrowRight className="h-3 w-3" />
          </a>
          <h1 className="mx-auto mt-7 max-w-4xl text-[36px] font-semibold leading-[1.1] tracking-[-0.03em] sm:text-[68px]">
            <span className="bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">你的个人投资智能体</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-[16px] leading-relaxed text-ink-3 sm:text-[18px]">
            记得你的持仓和投资风格，每天主动为你写简报，每一条买卖建议都会被复盘打分。覆盖 A 股、港股与美股。
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className="inline-flex h-11 items-center gap-2 rounded-xl bg-white px-6 text-[14px] font-medium text-black shadow-[0_0_0_1px_rgba(255,255,255,0.1),0_8px_30px_-6px_rgba(120,130,255,0.45)] hover:bg-white/90">
              免费注册，建立我的智能体 <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/login" className="inline-flex h-11 items-center rounded-xl border border-white/12 bg-white/[0.03] px-6 text-[14px] font-medium text-ink-2 hover:bg-white/[0.06] hover:text-ink">登录</Link>
          </div>
          {FEATURES.trial && (
            <p className="mt-4 text-[12.5px] text-ink-3">不想注册？<Link href="/try" className="text-ink-2 underline underline-offset-4 hover:text-ink">先随便问问</Link></p>
          )}
        </div>
        <div className="relative mx-auto max-w-6xl px-5 pb-24">
          <div className="pointer-events-none absolute inset-x-20 -top-6 h-40 rounded-full bg-brand/25 blur-3xl" />
          <Frame src="/images/landing/agent-home.png" alt="智能体首页：对话、今日简报、持仓异动与战绩" className="relative" />
        </div>
      </section>

      {/* values */}
      <section id="features" className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-6xl px-5 py-24">
          <p className="eyebrow text-center">为什么是「个人」投资智能体</p>
          <h2 className="mx-auto mt-3 max-w-2xl text-center text-[30px] font-semibold tracking-tight sm:text-[38px]">不是又一个聊天框，<br className="sm:hidden" />而是一个替你盯盘的研究助理</h2>
          <div className="mt-20 space-y-28">
            {VALUES.map((v, i) => (
              <div key={v.title} className="grid items-center gap-10 lg:grid-cols-[5fr_7fr] lg:gap-16">
                <div className={i % 2 ? "lg:order-2" : ""}>
                  <span className="inline-flex items-center gap-2 text-[13px] font-medium text-brand"><v.icon className="h-4 w-4" />{v.kicker}</span>
                  <h3 className="mt-3 text-[26px] font-semibold tracking-tight">{v.title}</h3>
                  <p className="mt-4 text-[15px] leading-relaxed text-ink-3">{v.desc}</p>
                  <ul className="mt-6 space-y-2.5">
                    {v.points.map((p) => (
                      <li key={p} className="flex items-center gap-2.5 text-[14px] text-ink-2"><span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/[0.06]"><Check className="h-3 w-3" /></span>{p}</li>
                    ))}
                  </ul>
                </div>
                <Frame src={v.img} alt={v.alt} className={i % 2 ? "lg:order-1" : ""} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* MCP */}
      <section id="mcp" className="border-t border-white/[0.06] bg-white/[0.015]">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-24 lg:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 text-[13px] font-medium text-brand"><Plug className="h-4 w-4" />MCP 原生</span>
            <h2 className="mt-3 text-[30px] font-semibold tracking-tight">在你常用的 AI 客户端里调用它</h2>
            <p className="mt-4 text-[15px] leading-relaxed text-ink-3">内置标准 MCP 服务（Streamable HTTP）。在智能体页面生成个人 Token，把下面的配置粘到 Cursor、Claude Desktop 或钉钉数字员工里，就能直接问「我的持仓今天怎么样」。</p>
            <div className="mt-6 flex flex-wrap gap-2">
              {["Claude Desktop", "Cursor", "钉钉数字员工", "任意 MCP 客户端"].map((c) => (
                <span key={c} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[13px] text-ink-2">{c}</span>
              ))}
            </div>
            <p className="eyebrow mt-8">可用工具</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {TOOLS.map((t) => <code key={t} className="rounded-md bg-white/[0.05] px-2 py-1 font-mono text-[11.5px] text-ink-3">{t}</code>)}
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-white/10 bg-[#0e0f13]">
            <div className="flex h-9 items-center justify-between border-b border-white/[0.06] px-4 text-[12px] text-ink-3">
              <span className="font-mono">~/.cursor/mcp.json</span>
              <span>Cursor</span>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[12.5px] leading-relaxed text-ink-2"><code>{MCP_JSON}</code></pre>
          </div>
        </div>
      </section>

      {/* final CTA */}
      <section className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-6xl px-5 py-24 text-center">
          <h2 className="text-[30px] font-semibold tracking-tight sm:text-[38px]">一分钟，建立你的投资智能体</h2>
          <p className="mx-auto mt-4 max-w-xl text-[15px] text-ink-3">注册 → 填写投资画像 → 添加持仓与自选。也可以用 Docker 一条命令自托管，只需要一个 LLM Key。</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/register" className="inline-flex h-11 items-center gap-2 rounded-xl bg-white px-6 text-[14px] font-medium text-black hover:bg-white/90">免费注册 <ArrowRight className="h-4 w-4" /></Link>
            <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center gap-2 rounded-xl border border-white/12 px-6 text-[14px] font-medium text-ink-2 hover:text-ink"><Github className="h-4 w-4" />自托管部署</a>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-10 text-[12px] text-ink-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-2"><BrandMark className="h-6 w-6 rounded-md" /><span className="text-ink-2">{BRAND.name}</span></div>
          <p className="flex max-w-2xl items-start gap-1.5 leading-relaxed"><ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />免责声明：本产品所有内容由 AI 基于公开数据自动生成，仅供研究与学习参考，不构成任何投资建议，亦不提供收益承诺。历史命中率不代表未来表现。投资有风险，决策需独立。</p>
        </div>
      </footer>
    </div>
  );
}
