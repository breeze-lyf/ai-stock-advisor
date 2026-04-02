"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/shared/api/client";

const POLL_INTERVAL_MS = 3 * 60 * 1000; // 每 3 分钟轮询一次

interface AnalysisStatusResult {
  /** 服务端有比当前展示更新的分析版本时为 true */
  hasNewAnalysis: boolean;
  /** 手动关闭 banner */
  dismiss: () => void;
}

/**
 * 轻量轮询 hook：定期查询 /api/v1/analysis/{ticker}/status，
 * 当服务端 last_analyzed_at 与本地 currentCreatedAt 不同时标记 hasNewAnalysis=true。
 *
 * @param ticker          当前查看的股票代码；为 null 时暂停轮询
 * @param currentCreatedAt  当前已加载分析的 created_at 时间戳字符串
 */
export function useAnalysisStatus(
  ticker: string | null,
  currentCreatedAt: string | undefined
): AnalysisStatusResult {
  const [hasNewAnalysis, setHasNewAnalysis] = useState(false);
  // Ref 避免闭包捕获旧值
  const currentCreatedAtRef = useRef(currentCreatedAt);

  // 用 render 阶段比较替代 useEffect 内同步 setState（React 推荐模式）
  const [prevTicker, setPrevTicker] = useState(ticker);
  const [prevCreatedAt, setPrevCreatedAt] = useState(currentCreatedAt);
  if (prevTicker !== ticker || prevCreatedAt !== currentCreatedAt) {
    setPrevTicker(ticker);
    setPrevCreatedAt(currentCreatedAt);
    setHasNewAnalysis(false);
  }

  // ref 更新放在 effect 中，避免在 render 阶段写入
  useEffect(() => {
    currentCreatedAtRef.current = currentCreatedAt;
  }, [currentCreatedAt]);

  useEffect(() => {
    if (!ticker) return;

    const poll = async () => {
      try {
        const res = await api.get<{ last_analyzed_at: string | null }>(
          `/api/v1/analysis/${encodeURIComponent(ticker)}/status`
        );
        const remoteAt = res.data.last_analyzed_at;
        if (
          remoteAt &&
          currentCreatedAtRef.current &&
          remoteAt !== currentCreatedAtRef.current
        ) {
          setHasNewAnalysis(true);
        }
      } catch {
        // 静默失败 —— 轮询是尽力而为的，不影响主流程
      }
    };

    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [ticker]);

  return {
    hasNewAnalysis,
    dismiss: () => setHasNewAnalysis(false),
  };
}
