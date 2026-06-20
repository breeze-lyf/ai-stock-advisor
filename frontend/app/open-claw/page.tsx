"use client";

import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Gauge,
  LineChart,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { useMemo, useState } from "react";

const tenders = [
  {
    city: "江苏省",
    notice: "脊柱耗材省际联盟续约",
    deadline: "48小时",
    sku: "SP-2201 椎弓根钉",
    amount: 1820,
    risk: "低价联动触发",
    confidence: 92,
    action: "报价需高于红线 7.8%，建议走总监特批",
  },
  {
    city: "浙江省",
    notice: "冠脉球囊挂网补充申报",
    deadline: "3天",
    sku: "CB-3108 药物涂层球囊",
    amount: 760,
    risk: "注册证有效期不足",
    confidence: 87,
    action: "补齐延续受理通知书，经销商先提交承诺函",
  },
  {
    city: "山东省",
    notice: "骨科创伤带量采购接续",
    deadline: "6天",
    sku: "TR-1419 锁定接骨板",
    amount: 1240,
    risk: "竞品降价 11%",
    confidence: 81,
    action: "保留三甲样板院份额，非核心包放弃跟价",
  },
  {
    city: "福建省",
    notice: "一次性电生理导管阳光采购",
    deadline: "9天",
    sku: "EP-7702 标测导管",
    amount: 540,
    risk: "配送商覆盖不足",
    confidence: 78,
    action: "启用备选配送商，先锁 17 家目标医院",
  },
];

const feedbackLoop = [
  "公告抓取：医保局、交易中心、联盟采购平台每 20 分钟增量比对",
  "材料核验：注册证、授权链、价格红线、经销商覆盖率自动打分",
  "人工介入：低置信度或触发价格红线时推送准入经理复核",
  "纠错回灌：复核理由写回规则库，更新相似公告的风险阈值",
];

const roiInputs = {
  avgManagerCost: 36000,
  monthlyNotices: 420,
  currentLeakRate: 0.09,
  personaLeakRate: 0.024,
  avgTenderGrossProfit: 180000,
  manualHoursPerNotice: 1.4,
  personaHoursPerNotice: 0.28,
};

function formatMoney(value: number) {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万`;
  }
  return value.toLocaleString("zh-CN");
}

export default function OpenClawPersonaPage() {
  const [reviewLevel, setReviewLevel] = useState<"strict" | "balanced" | "speed">("balanced");
  const [selectedTender, setSelectedTender] = useState(tenders[0]);

  const multiplier = reviewLevel === "strict" ? 0.82 : reviewLevel === "speed" ? 1.18 : 1;
  const roi = useMemo(() => {
    const savedHours =
      roiInputs.monthlyNotices *
      (roiInputs.manualHoursPerNotice - roiInputs.personaHoursPerNotice) *
      multiplier;
    const laborSaved = savedHours * 280;
    const recoveredLeads =
      roiInputs.monthlyNotices *
      (roiInputs.currentLeakRate - roiInputs.personaLeakRate) *
      roiInputs.avgTenderGrossProfit *
      multiplier;
    const approvalDaysSaved = reviewLevel === "strict" ? 4.1 : reviewLevel === "speed" ? 6.8 : 5.6;

    return {
      savedHours: Math.round(savedHours),
      laborSaved: Math.round(laborSaved),
      recoveredLeads: Math.round(recoveredLeads),
      monthlyValue: Math.round(laborSaved + recoveredLeads),
      approvalDaysSaved,
      payback: ((laborSaved + recoveredLeads) / 198000).toFixed(1),
    };
  }, [multiplier, reviewLevel]);

  return (
    <div className="min-h-screen bg-[#f7f8f3] text-neutral-950">
      <header className="border-b border-neutral-200 bg-white/86 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md bg-emerald-700 text-white">
              <Bot className="size-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Open Claw Enterprise Avatar Lab</p>
              <p className="text-xs text-neutral-500">高值医疗器械准入投标分身</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 text-sm text-neutral-500 sm:flex">
            <ShieldCheck className="size-4 text-emerald-700" />
            人审闭环 · 报价红线 · 经销商协同
          </div>
        </div>
      </header>

      <main>
        <section className="border-b border-neutral-200 bg-[#fbfcf8]">
          <div className="mx-auto grid max-w-7xl gap-8 px-5 py-10 lg:grid-cols-[1.02fr_0.98fr] lg:py-14">
            <div className="flex flex-col justify-center">
              <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800">
                <Sparkles className="size-4" />
                最具变现潜力靶点：械企省级准入经理
              </div>
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-neutral-950 md:text-6xl">
                MedAccess Bid Twin
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-neutral-600">
                它不是客服，而是替高值耗材企业的“省级挂网、集采续约、经销商材料、价格红线审批”连续值守。
                目标是减少漏申报、错报价和审批等待，把每一条公告变成可执行的投标动作。
              </p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {[
                  ["月度可回收价值", formatMoney(roi.monthlyValue), "线索挽回 + 人效节省"],
                  ["审批压缩", `${roi.approvalDaysSaved}天`, "报价与材料并行预审"],
                  ["年化回本倍数", `${roi.payback}x`, "按 19.8 万/月订阅测算"],
                ].map(([label, value, hint]) => (
                  <div key={label} className="rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
                    <p className="text-xs font-medium uppercase text-neutral-500">{label}</p>
                    <p className="mt-2 text-2xl font-semibold text-neutral-950">{value}</p>
                    <p className="mt-1 text-xs text-neutral-500">{hint}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold">今日公告驾驶舱</p>
                  <p className="text-xs text-neutral-500">模拟数据：4 省公告、31 个 SKU、63 家目标医院</p>
                </div>
                <Gauge className="size-5 text-emerald-700" />
              </div>
              <div className="space-y-3">
                {tenders.map((tender) => (
                  <button
                    key={`${tender.city}-${tender.sku}`}
                    onClick={() => setSelectedTender(tender)}
                    className={`w-full rounded-md border p-4 text-left transition ${
                      selectedTender.sku === tender.sku
                        ? "border-emerald-500 bg-emerald-50"
                        : "border-neutral-200 bg-white hover:border-neutral-300"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold">{tender.city} · {tender.notice}</p>
                        <p className="mt-1 text-sm text-neutral-500">{tender.sku}</p>
                      </div>
                      <span className="rounded-md bg-neutral-900 px-2.5 py-1 text-xs font-medium text-white">
                        {tender.deadline}
                      </span>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-sm text-amber-700">
                      <AlertTriangle className="size-4" />
                      {tender.risk}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-6 px-5 py-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <FileSearch className="size-5 text-emerald-700" />
              <h2 className="text-xl font-semibold">样本处理结果</h2>
            </div>
            <div className="mt-5 space-y-4">
              <div className="rounded-md bg-neutral-50 p-4">
                <p className="text-sm text-neutral-500">当前公告</p>
                <p className="mt-1 font-semibold">{selectedTender.city} · {selectedTender.notice}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Metric label="预测毛利池" value={`${selectedTender.amount}万`} icon={<BarChart3 className="size-4" />} />
                <Metric label="模型置信度" value={`${selectedTender.confidence}%`} icon={<BadgeCheck className="size-4" />} />
              </div>
              <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                  <AlertTriangle className="size-4" />
                  风险判断
                </p>
                <p className="mt-2 text-sm leading-6 text-amber-900">{selectedTender.risk}</p>
              </div>
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                  <ClipboardCheck className="size-4" />
                  分身建议动作
                </p>
                <p className="mt-2 text-sm leading-6 text-emerald-900">{selectedTender.action}</p>
              </div>
            </div>
          </div>

          <div className="rounded-md border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="size-5 text-emerald-700" />
                <h2 className="text-xl font-semibold">ROI 动态测算</h2>
              </div>
              <div className="flex rounded-md border border-neutral-200 bg-neutral-50 p-1">
                {[
                  ["strict", "稳健"],
                  ["balanced", "均衡"],
                  ["speed", "抢时效"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setReviewLevel(key as "strict" | "balanced" | "speed")}
                    className={`rounded px-3 py-1.5 text-sm font-medium ${
                      reviewLevel === key ? "bg-white text-emerald-800 shadow-sm" : "text-neutral-500"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <Metric label="月节省人时" value={`${roi.savedHours}h`} icon={<UserCheck className="size-4" />} />
              <Metric label="漏申报挽回" value={formatMoney(roi.recoveredLeads)} icon={<LineChart className="size-4" />} />
              <Metric label="综合月价值" value={formatMoney(roi.monthlyValue)} icon={<CheckCircle2 className="size-4" />} />
            </div>
            <div className="mt-6 overflow-hidden rounded-md border border-neutral-200">
              <div className="grid grid-cols-[1.2fr_0.8fr_0.8fr] bg-neutral-900 px-4 py-3 text-sm font-semibold text-white">
                <span>成本项</span>
                <span>传统模式</span>
                <span>分身模式</span>
              </div>
              {[
                ["公告初筛", "420 条/月 × 1.4h", "420 条/月 × 0.28h"],
                ["漏申报率", "9.0%", "2.4%"],
                ["报价审批周期", "7-12 天", `${roi.approvalDaysSaved} 天压缩`],
                ["复核覆盖", "经理抽查", "高风险 100% 人审"],
              ].map((row) => (
                <div key={row[0]} className="grid grid-cols-[1.2fr_0.8fr_0.8fr] border-t border-neutral-200 px-4 py-3 text-sm">
                  <span className="font-medium">{row[0]}</span>
                  <span className="text-neutral-500">{row[1]}</span>
                  <span className="text-emerald-800">{row[2]}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-y border-neutral-200 bg-white">
          <div className="mx-auto max-w-7xl px-5 py-8">
            <div className="mb-6 flex items-center gap-2">
              <Bot className="size-5 text-emerald-700" />
              <h2 className="text-xl font-semibold">深度陪跑机制</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-4">
              {feedbackLoop.map((item, index) => (
                <div key={item} className="rounded-md border border-neutral-200 bg-[#fbfcf8] p-4">
                  <div className="mb-4 flex size-8 items-center justify-center rounded-md bg-emerald-700 text-sm font-semibold text-white">
                    {index + 1}
                  </div>
                  <p className="text-sm leading-6 text-neutral-700">{item}</p>
                  {index < feedbackLoop.length - 1 && (
                    <ArrowRight className="mt-4 hidden size-4 text-neutral-400 md:block" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-8">
          <div className="grid gap-6 lg:grid-cols-[0.82fr_1.18fr]">
            <div>
              <h2 className="text-2xl font-semibold">产品动态说明</h2>
              <p className="mt-3 leading-7 text-neutral-600">
                V0.1 版本聚焦“公告到投标动作”的单点闭环：先让准入经理少漏、少错、少等。
                后续每周根据人工复核记录和中标结果更新规则，逐步沉淀企业自己的准入知识库。
              </p>
            </div>
            <div className="space-y-3">
              {[
                ["Day 1", "导入历史中标、SKU、注册证、经销商授权链，生成价格红线与材料缺口清单"],
                ["Week 1", "上线省级公告监听和风险分流，低置信度任务自动进入准入经理工作台"],
                ["Month 1", "接入 CRM 与合同毛利数据，按省份、产品线、医院等级输出 ROI 看板"],
                ["Quarter 1", "用人工复核和真实中标结果校准阈值，形成企业级准入策略资产"],
              ].map(([time, text]) => (
                <div key={time} className="rounded-md border border-neutral-200 bg-white p-4 shadow-sm">
                  <p className="text-sm font-semibold text-emerald-800">{time}</p>
                  <p className="mt-1 text-sm leading-6 text-neutral-700">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3 text-neutral-500">
        <span className="text-xs font-medium uppercase">{label}</span>
        {icon}
      </div>
      <p className="mt-3 text-2xl font-semibold text-neutral-950">{value}</p>
    </div>
  );
}
