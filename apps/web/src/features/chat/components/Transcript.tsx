"use client";

import { motion } from "framer-motion";
import { useEffect, useRef } from "react";

import { Loader } from "@/components/common/Loader";
import { errorCodeText } from "@/lib/i18n/errorText";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";

import type { ChatMessage } from "../hooks/useAssistantTurn";

export function Transcript({
  messages,
  interim,
  activeTool,
}: {
  messages: ChatMessage[];
  interim?: string;
  activeTool?: string | null;
}) {
  const t = useT();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, interim]);

  return (
    <div
      role="log"
      aria-live="polite"
      aria-label={t("console.title")}
      data-testid="transcript"
      className="flex flex-col gap-3"
    >
      {messages.map((m) => (
        <motion.div
          key={m.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap",
            m.role === "user"
              ? "self-end rounded-br-sm bg-primary text-primary-foreground"
              : "self-start rounded-bl-sm border bg-card",
            m.status === "error" && "border-destructive/40 bg-destructive/5",
          )}
          data-role={m.role}
          data-status={m.status}
        >
          <span className="sr-only">
            {m.role === "user" ? t("console.you") : t("console.saathi")}:{" "}
          </span>
          {m.status === "error" ? errorCodeText(t, m.errorCode) : m.text}
          {m.role === "assistant" && m.status === "streaming" && !m.text ? (
            <Loader size="sm" label={t("common.loading")} />
          ) : null}
          {m.status === "streaming" && m.text ? (
            <span
              aria-hidden="true"
              className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-current align-middle"
            />
          ) : null}
          {m.role === "assistant" && (m.model || m.requestId) ? (
            <span className="mt-1 block text-[11px] opacity-60">
              {[
                m.model ? t("console.model", { model: m.model }) : null,
                m.requestId ? t("common.requestId", { id: m.requestId }) : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          ) : null}
        </motion.div>
      ))}
      {activeTool ? (
        <p className="self-start text-xs text-muted-foreground">
          {t("console.tool", { skill: activeTool })}
        </p>
      ) : null}
      {interim ? (
        <p className="max-w-[85%] self-end rounded-2xl border border-dashed px-4 py-3 text-sm italic opacity-70">
          {interim}
        </p>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}
