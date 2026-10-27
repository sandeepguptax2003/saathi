"use client";

import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/I18nProvider";

import { Loader } from "./Loader";

export interface WakingSaathiProps {
  elapsedSeconds: number;
  failed?: boolean;
  onRetry?: () => void;
}

/** Non-blocking banner shown while the free-tier API cold-starts (Render sleeps after ~15 min idle). */
export function WakingSaathi({ elapsedSeconds, failed, onRetry }: WakingSaathiProps) {
  const t = useT();
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center px-4"
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-xl border bg-card p-3 shadow-lg"
      >
        <span aria-hidden="true" className="text-2xl">
          🪔
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{failed ? t("wake.failed") : t("wake.title")}</p>
          <p className="text-xs text-muted-foreground">{t("wake.body")}</p>
        </div>
        {failed ? (
          <Button size="sm" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <Loader size="sm" label={t("wake.title")} />
            <span className="font-mono text-xs text-muted-foreground">
              {t("wake.elapsed", { s: elapsedSeconds })}
            </span>
          </div>
        )}
      </motion.div>
    </div>
  );
}
