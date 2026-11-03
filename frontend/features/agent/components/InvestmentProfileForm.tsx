"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { getInvestmentProfile, saveInvestmentProfile, type InvestmentProfile } from "@/features/agent/api";

export const RISK_OPTS = [
  { v: "CONSERVATIVE", l: "保守", score: 3, d: "本金安全优先，能接受小幅波动" },
  { v: "MODERATE", l: "稳健", score: 6, d: "追求收益与风险平衡" },
  { v: "AGGRESSIVE", l: "积极", score: 8, d: "追求高收益，能承受较大回撤" },
] as const;
export const HORIZON_OPTS = [
  { v: "SHORT", l: "短线（数天~数周）" },
  { v: "MEDIUM", l: "中线（1~6 个月）" },
  { v: "LONG", l: "长线（1 年以上）" },
] as const;
export const STYLE_OPTS = [
  { v: "VALUE", l: "价值" },
  { v: "GROWTH", l: "成长" },
  { v: "MOMENTUM", l: "趋势/动量" },
  { v: "INCOME", l: "红利/收息" },
] as const;
export const MARKET_OPTS = [
  { v: "CN", l: "A 股" },
  { v: "HK", l: "港股" },
  { v: "US", l: "美股" },
] as const;

const DEFAULT: InvestmentProfile = { risk_tolerance: "MODERATE", risk_tolerance_score: 6, investment_experience: "INTERMEDIATE", preferred_markets: ["CN", "US"], investment_style: "GROWTH", investment_horizon: "MEDIUM" };

function Chips<T extends string>({ opts, value, onChange }: { opts: readonly { v: T; l: string }[]; value: (v: T) => boolean; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {opts.map((o) => (
        <button key={o.v} type="button" onClick={() => onChange(o.v)} className={clsx("rounded-md border px-3 py-1.5 text-sm transition", value(o.v) ? "border-ink bg-elevated text-ink" : "border-line text-ink-2 hover:border-line")}>{o.l}</button>
      ))}
    </div>
  );
}

/** 投资画像：风险 / 周期 / 风格 / 市场。保存后智能体每次对话、每日简报都会参考。 */
export function InvestmentProfileForm() {
  const [p, setP] = useState<InvestmentProfile>(DEFAULT);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    getInvestmentProfile().then((r) => r && setP({ ...DEFAULT, ...r })).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await saveInvestmentProfile(p);
      setMsg("已保存，智能体下一次回答起就会按新画像思考。");
    } catch {
      setMsg("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-sm text-ink-3">加载中…</p>;
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className="text-sm font-semibold">风险偏好</p>
        <Chips opts={RISK_OPTS} value={(v) => p.risk_tolerance === v} onChange={(v) => setP({ ...p, risk_tolerance: v, risk_tolerance_score: RISK_OPTS.find((o) => o.v === v)!.score })} />
        <p className="text-xs text-ink-3">{RISK_OPTS.find((o) => o.v === p.risk_tolerance)?.d}</p>
      </div>
      <div className="space-y-2">
        <p className="text-sm font-semibold">持有周期</p>
        <Chips opts={HORIZON_OPTS} value={(v) => p.investment_horizon === v} onChange={(v) => setP({ ...p, investment_horizon: v })} />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-semibold">投资风格</p>
        <Chips opts={STYLE_OPTS} value={(v) => p.investment_style === v} onChange={(v) => setP({ ...p, investment_style: v })} />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-semibold">关注市场（可多选）</p>
        <Chips opts={MARKET_OPTS} value={(v) => p.preferred_markets.includes(v)} onChange={(v) => setP({ ...p, preferred_markets: p.preferred_markets.includes(v) ? p.preferred_markets.filter((x) => x !== v) : [...p.preferred_markets, v] })} />
      </div>
      <div className="flex items-center gap-3">
        <button type="button" onClick={save} disabled={saving} className="flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-canvas disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />} 保存画像</button>
        {msg && <span className="text-xs text-ink-3">{msg}</span>}
      </div>
    </div>
  );
}
