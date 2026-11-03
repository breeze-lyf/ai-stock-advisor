"use client";

import { useEffect, useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { createNotifier, deleteNotifier, listNotifiers, testNotifier, type NotifierConfig } from "@/features/agent/api";

const KINDS = {
  dingtalk: { l: "钉钉群机器人", url: "Webhook 地址（https://oapi.dingtalk.com/robot/send?access_token=…）", secret: "加签密钥 SEC…（可选，推荐）" },
  webhook: { l: "通用 Webhook", url: "https://your.server/hook（POST JSON：title / text / type）", secret: "（通用 Webhook 无需密钥，留空即可）" },
  telegram: { l: "Telegram（可选）", url: "Chat ID，例如 123456789", secret: "Bot Token" },
} as const;
type Kind = keyof typeof KINDS;

/** 推送渠道：每日简报 / 测试消息会发送到这里。URL 与密钥加密存储。 */
export function NotifierSettings() {
  const [items, setItems] = useState<NotifierConfig[]>([]);
  const [kind, setKind] = useState<Kind>("dingtalk");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => listNotifiers().then(setItems).catch(() => setMsg("加载失败"));
  useEffect(() => { load(); }, []);

  const err = (e: unknown, d: string) => (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || d;

  const add = async () => {
    setBusy("add");
    setMsg(null);
    try {
      await createNotifier({ kind, url: url.trim(), secret: secret.trim() || undefined });
      setUrl("");
      setSecret("");
      setMsg("已添加，可点击「发送测试」验证。");
      load();
    } catch (e) {
      setMsg(err(e, "添加失败"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-neutral-500">还没有推送渠道。添加后，每日简报会自动推送到这里。</p>}
        {items.map((n) => (
          <div key={n.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-neutral-200 px-4 py-3 dark:border-neutral-800">
            <div className="min-w-0">
              <p className="text-sm font-semibold">{KINDS[n.kind]?.l ?? n.kind} {n.has_secret && <span className="ml-1 text-[10px] text-emerald-600">已加签</span>}</p>
              <p className="truncate text-xs text-neutral-500">{n.url}{n.last_status ? ` · 最近：${n.last_status}` : ""}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" disabled={!!busy} onClick={async () => { setBusy(n.id); try { const r = await testNotifier(n.id); setMsg(r.ok ? "测试消息已发送 ✓" : `发送失败：${r.message}`); load(); } catch (e) { setMsg(err(e, "发送失败")); } finally { setBusy(null); } }} className="flex items-center gap-1 rounded-lg border border-neutral-300 px-2.5 py-1 text-xs dark:border-neutral-700">{busy === n.id && <Loader2 className="h-3 w-3 animate-spin" />} 发送测试</button>
              <button type="button" disabled={!!busy} onClick={async () => { await deleteNotifier(n.id).catch(() => undefined); load(); }} className="rounded-lg p-1.5 text-neutral-400 hover:text-rose-600" title="删除"><Trash2 className="h-4 w-4" /></button>
            </div>
          </div>
        ))}
      </div>
      <div className="space-y-3 rounded-2xl border border-dashed border-neutral-300 p-4 dark:border-neutral-700">
        <p className="text-sm font-semibold">添加渠道</p>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(KINDS) as Kind[]).map((k) => (
            <button key={k} type="button" onClick={() => setKind(k)} className={`rounded-xl border px-3 py-1.5 text-sm ${kind === k ? "border-blue-600 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300" : "border-neutral-200 dark:border-neutral-700"}`}>{KINDS[k].l}</button>
          ))}
        </div>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder={KINDS[kind].url} className="w-full rounded-xl border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700" />
        <input value={secret} onChange={(e) => setSecret(e.target.value)} placeholder={KINDS[kind].secret} type="password" autoComplete="off" className="w-full rounded-xl border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700" />
        <button type="button" onClick={add} disabled={!url.trim() || busy === "add" || (kind === "telegram" && !secret.trim())} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">添加</button>
        {kind === "dingtalk" && <p className="text-xs text-neutral-500">钉钉群 → 群设置 → 机器人 → 添加自定义机器人，安全设置选「加签」，把 Webhook 与 SEC 密钥填到上面。</p>}
      </div>
      {msg && <p className="text-sm text-neutral-600 dark:text-neutral-300">{msg}</p>}
    </div>
  );
}
