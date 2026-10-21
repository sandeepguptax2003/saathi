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

/** Shown while the free-tier API cold-starts (Render sleeps after ~15 min idle). */
export function WakingSaathi({ elapsedSeconds, failed, onRetry }: WakingSaathiProps) {
  const t = useT();
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-40 flex items-center justify-center bg-background/85 backdrop-blur-sm"
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-4 flex max-w-sm flex-col items-center gap-4 rounded-2xl border bg-card p-8 text-center shadow-lg"
      >
        <motion.div
          aria-hidden="true"
          className="flex size-16 items-center justify-center rounded-full bg-primary/15 text-3xl"
          animate={failed ? undefined : { scale: [1, 1.08, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          🪔
        </motion.div>
        <h2 className="text-lg font-semibold">{failed ? t("wake.failed") : t("wake.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("wake.body")}</p>
        {failed ? (
          <Button onClick={onRetry}>{t("common.retry")}</Button>
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
