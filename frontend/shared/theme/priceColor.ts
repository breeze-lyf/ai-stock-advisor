"use client";

import { useSyncExternalStore } from "react";

/** 涨跌配色偏好。green_up = 绿涨红跌（默认），red_up = 红涨绿跌。 */
export type PriceColorMode = "green_up" | "red_up";
export const DEFAULT_PRICE_COLOR_MODE: PriceColorMode = "green_up";
const KEY = "price_color_mode";
const EVT = "price-color-mode";

/** 供 canvas 图表（K 线）使用的十六进制色值；与 globals.css 中的 --red / --green 对应。 */
export const PRICE_HEX = { red: "#e5484d", green: "#30a46c" } as const;

export function normalizeMode(v: unknown): PriceColorMode {
  return v === "red_up" ? "red_up" : "green_up";
}

export function getPriceColorMode(): PriceColorMode {
  if (typeof window === "undefined") return DEFAULT_PRICE_COLOR_MODE;
  try { return normalizeMode(localStorage.getItem(KEY)); } catch { return DEFAULT_PRICE_COLOR_MODE; }
}

/** 立即应用并缓存到 localStorage（登录前页面也能用）。 */
export function applyPriceColorMode(mode: PriceColorMode) {
  if (typeof window === "undefined") return;
  document.documentElement.dataset.updown = mode;
  try { localStorage.setItem(KEY, mode); } catch { /* ignore */ }
  window.dispatchEvent(new CustomEvent(EVT, { detail: mode }));
}

export function priceHex(mode: PriceColorMode) {
  return mode === "red_up" ? { up: PRICE_HEX.red, down: PRICE_HEX.green } : { up: PRICE_HEX.green, down: PRICE_HEX.red };
}

function subscribe(cb: () => void) {
  window.addEventListener(EVT, cb);
  window.addEventListener("storage", cb);
  return () => { window.removeEventListener(EVT, cb); window.removeEventListener("storage", cb); };
}

export function usePriceColorMode(): PriceColorMode {
  return useSyncExternalStore(subscribe, getPriceColorMode, () => DEFAULT_PRICE_COLOR_MODE);
}
