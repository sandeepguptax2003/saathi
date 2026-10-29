"use client";

import { AlertTriangleIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { isApiError } from "@/lib/api/errors";
import { errorText } from "@/lib/i18n/errorText";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  error?: unknown;
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ error, title, message, onRetry, className }: ErrorStateProps) {
  const t = useT();
  const requestId = isApiError(error) ? error.requestId : undefined;
  const detail = message ?? errorText(t, error);
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center",
        className,
      )}
    >
      <AlertTriangleIcon aria-hidden="true" className="size-8 text-destructive" />
      <h3 className="font-semibold">{title ?? t("common.somethingWrong")}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{detail}</p>
      {requestId ? (
        <p className="font-mono text-xs text-muted-foreground">
          {t("common.requestId", { id: requestId })}
        </p>
      ) : null}
      {onRetry ? (
        <Button variant="outline" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      ) : null}
    </div>
  );
}
