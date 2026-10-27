"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn, formatUsd } from "@/lib/utils";

import { useBudgetUsage } from "../hooks/useBudgetUsage";

export function BudgetMeter() {
  const t = useT();
  const query = useBudgetUsage("day");
  if (query.isError) return null; // Non-critical widget; hide when unavailable.
  const usage = query.data;
  const pct = usage && usage.capUsd > 0 ? Math.min(100, (usage.spentUsd / usage.capUsd) * 100) : 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("budget.title")}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {!usage ? (
          <Skeleton className="h-3 w-full" />
        ) : (
          <>
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(pct)}
              className="h-3 w-full overflow-hidden rounded-full bg-muted"
            >
              <div
                className={cn("h-full rounded-full", pct >= 70 ? "bg-destructive" : "bg-primary")}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {t("budget.of", {
                spent: formatUsd(usage.spentUsd),
                cap: formatUsd(usage.capUsd, 2),
              })}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
