"use client";

import { AnimatePresence, motion } from "framer-motion";
import { MicIcon, MicOffIcon, SquareIcon } from "lucide-react";

import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";

export interface MicButtonProps {
  listening: boolean;
  supported: boolean;
  disabled?: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function MicButton({ listening, supported, disabled, onStart, onStop }: MicButtonProps) {
  const t = useT();
  const label = !supported
    ? t("console.noStt")
    : listening
      ? t("console.mic.stop")
      : t("console.mic.start");

  return (
    <div className="relative flex size-24 items-center justify-center">
      <AnimatePresence>
        {listening
          ? [0, 1].map((ring) => (
              <motion.span
                key={ring}
                aria-hidden="true"
                className="absolute inset-0 rounded-full bg-primary/25"
                initial={{ scale: 0.8, opacity: 0.7 }}
                animate={{ scale: 1.5, opacity: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.6, repeat: Infinity, delay: ring * 0.8 }}
              />
            ))
          : null}
      </AnimatePresence>
      <motion.button
        type="button"
        whileTap={{ scale: 0.94 }}
        aria-pressed={listening}
        aria-label={label}
        title={label}
        disabled={!supported || disabled}
        onClick={listening ? onStop : onStart}
        className={cn(
          "relative z-10 flex size-20 items-center justify-center rounded-full shadow-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          listening
            ? "bg-destructive text-destructive-foreground"
            : "bg-primary text-primary-foreground",
        )}
      >
        {!supported ? (
          <MicOffIcon aria-hidden="true" className="size-8" />
        ) : listening ? (
          <SquareIcon aria-hidden="true" className="size-7" />
        ) : (
          <MicIcon aria-hidden="true" className="size-8" />
        )}
      </motion.button>
    </div>
  );
}
