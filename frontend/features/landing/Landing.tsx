"use client";

import Link from "next/link";
import { ArrowRight, Github, ShieldAlert } from "lucide-react";
import { BRAND, FEATURES } from "@/shared/config/features";
import { BrandMark } from "@/components/features/DashboardHeader";

const REPO = "https://github.com/breeze-lyf/ai-stock-advisor";

const PILLARS = [
  {
    title: "记得你的持仓与风格",
    body: "风险偏好、持有周期、关注市场，加上持仓与自选，都会进入上下文。同一个问题，不同画像得到不同回答。",
  },
  {
    title: "每天一份简报",
    body: "盘前梳理涨跌、新闻与风险，可推送到钉钉、Webhook 或 Telegram。只针对你的标的，不是全市场噪音。",
  },
  {
    title: "每条建议可复盘",
    body: "买入、卖出、持有建议连同当时价格与理由入档，到期按真实行情打分。命中与否，可查。",
  },
];

function Frame({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-surface">
      <div className="flex h-9 items-center gap-2 border-b border-line bg-elevated/80 px-3">
        <span className="h-2 w-2 rounded-full bg-line-strong" />
        <span className="h-2 w-2 rounded-full bg-line-strong" />
        <span className="h-2 w-2 rounded-full bg-line-strong" />
        <span className="ml-2 truncate text-[11px] text-ink-3">{BRAND.name}</span>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="block w-full" loading="eager" />
    </div>
  );
}

export function Landing() {
  return (
    <div className="min-h-screen bg-canvas text-ink antialiased">
      <header className="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-5">
          <Link href="/" className="flex items-center gap-2.5">
            <BrandMark className="h-7 w-7 rounded-md" />
            <span className="text-[14px] font-semibold tracking-tight">{BRAND.name}</span>
          </Link>
          <nav className="hidden items-center gap-6 text-[13px] text-ink-3 md:flex">
            <a href="#product" className="hover:text-ink">产品</a>
            <a href="#pillars" className="hover:text-ink">能力</a>
            <a href={REPO} target="_blank" rel="noreferrer" className="hover:text-ink">GitHub</a>
          </nav>
          <div className="flex items-center gap-1.5">
            <Link href="/login" className="h-8 rounded-md px-3 text-[13px] leading-8 text-ink-2 hover:text-ink">登录</Link>
            <Link href="/register" className="h-8 rounded-md bg-ink px-3 text-[13px] font-medium leading-8 text-canvas hover:opacity-90">注册</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-5 pb-10 pt-16 sm:pt-20">
        <div className="max-w-2xl">
          <h1 className="text-[34px] font-semibold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[44px]">
            你的个人投资智能体
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-2 sm:text-[16px]">
            记得持仓与投资风格，每天写简报，每条买卖建议会被复盘。覆盖 A 股、港股与美股。
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/register" className="inline-flex h-10 items-center gap-1.5 rounded-md bg-ink px-5 text-[13.5px] font-medium text-canvas hover:opacity-90">
              注册 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link href="/login" className="inline-flex h-10 items-center rounded-md border border-line bg-surface px-5 text-[13.5px] font-medium text-ink-2 hover:border-line-strong hover:text-ink">
              登录
            </Link>
          </div>
          {FEATURES.trial && (
            <p className="mt-3 text-[12px] text-ink-3">不想注册？<Link href="/try" className="underline underline-offset-4 hover:text-ink">先随便问问</Link></p>
          )}
          <p className="mt-6 text-[12px] text-ink-3">
            开源可自托管 · <a href="#integrations" className="underline underline-offset-4 hover:text-ink">MCP 接入说明</a>
          </p>
        </div>

        <div id="product" className="mt-14">
          <Frame src="/images/landing/agent-home.png" alt="智能体工作台：对话、简报、持仓异动与复盘" />
        </div>
      </section>

      <section id="pillars" className="border-t border-line">
        <div className="mx-auto grid max-w-5xl gap-10 px-5 py-16 sm:grid-cols-3 sm:gap-8">
          {PILLARS.map((p) => (
            <div key={p.title}>
              <h2 className="text-[15px] font-semibold tracking-tight text-ink">{p.title}</h2>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-2">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="integrations" className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-5 py-12 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-[15px] font-semibold text-ink">在 Cursor / Claude / 钉钉里调用</h2>
            <p className="mt-1 max-w-xl text-[13px] leading-relaxed text-ink-3">
              内置 MCP（Streamable HTTP）。登录后在智能体侧栏生成 Token，即可在常用客户端问「我的持仓今天怎么样」。
            </p>
          </div>
          <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md border border-line bg-surface px-3.5 text-[13px] text-ink-2 hover:border-line-strong hover:text-ink">
            <Github className="h-3.5 w-3.5" /> 查看部署与 MCP 文档
          </a>
        </div>
      </section>

      <section className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-6 px-5 py-14 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-[20px] font-semibold tracking-tight text-ink">建立你的投资智能体</h2>
            <p className="mt-1.5 text-[13.5px] text-ink-3">注册 → 填写画像 → 添加持仓。也可 Docker 自托管。</p>
          </div>
          <div className="flex gap-2">
            <Link href="/register" className="inline-flex h-10 items-center rounded-md bg-ink px-5 text-[13.5px] font-medium text-canvas hover:opacity-90">注册</Link>
            <Link href="/login" className="inline-flex h-10 items-center rounded-md border border-line px-5 text-[13.5px] text-ink-2 hover:text-ink">登录</Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 px-5 py-8 text-[12px] text-ink-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-2">
            <BrandMark className="h-5 w-5 rounded" />
            <span className="text-ink-2">{BRAND.name}</span>
          </div>
          <p className="flex max-w-2xl items-start gap-1.5 leading-relaxed">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            免责声明：内容由 AI 基于公开数据生成，仅供研究参考，不构成投资建议。历史命中率不代表未来表现。
          </p>
        </div>
      </footer>
    </div>
  );
}
