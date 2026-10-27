"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { checkHealth } from "@/lib/api/health";
import { env } from "@/lib/env";

export type WakeStatus = "checking" | "waking" | "ready" | "failed";

export interface UseApiWakeOptions {
  /** Show the "waking" overlay only if the first ping is slower than this. */
  graceMs?: number;
  pollMs?: number;
  giveUpMs?: number;
}

/**
 * Pings GET /health until the free-tier API answers (Render cold start can take ~1 min).
 * Render holds a request open while the instance boots, so each ping waits up to 60 s.
 */
export function useApiWake({
  graceMs = 1500,
  pollMs = 2000,
  giveUpMs = 180_000,
}: UseApiWakeOptions = {}) {
  const [status, setStatus] = useState<WakeStatus>("checking");
  const [elapsed, setElapsed] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    const startedAt = Date.now();
    setStatus("checking");
    setElapsed(0);
    const grace = setTimeout(() => {
      if (!cancelled.current) setStatus((s) => (s === "checking" ? "waking" : s));
    }, graceMs);
    const ticker = setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 1000);

    (async () => {
      while (!cancelled.current) {
        if (await checkHealth(env.NEXT_PUBLIC_API_URL, 60_000)) {
          if (!cancelled.current) setStatus("ready");
          return;
        }
        if (Date.now() - startedAt > giveUpMs) {
          if (!cancelled.current) setStatus("failed");
          return;
        }
        if (!cancelled.current) setStatus("waking");
        await new Promise((r) => setTimeout(r, pollMs));
      }
    })().finally(() => {
      clearTimeout(grace);
      clearInterval(ticker);
    });

    return () => {
      cancelled.current = true;
      clearTimeout(grace);
      clearInterval(ticker);
    };
  }, [attempt, graceMs, pollMs, giveUpMs]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { status, elapsed, retry };
}
