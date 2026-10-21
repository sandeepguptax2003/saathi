"use client";

import { EyeOffIcon } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/lib/i18n/I18nProvider";
import type { EntityCounts } from "@/types/api";

import { EntityCountList } from "./EntityCountList";

/** Console side panel: what the model saw for the latest turn (counts only). */
export function PrivacyPanel({ counts }: { counts: EntityCounts | null }) {
  const t = useT();
  const total = counts ? Object.values(counts).reduce((sum, n) => sum + n, 0) : 0;
  return (
    <Card data-testid="privacy-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <EyeOffIcon aria-hidden="true" className="size-4 text-primary" />
          {t("privacy.panel.title")}
        </CardTitle>
        <CardDescription>{t("privacy.panel.body")}</CardDescription>
      </CardHeader>
      <CardContent>
        {counts === null ? (
          <p className="text-sm text-muted-foreground">{t("privacy.panel.waiting")}</p>
        ) : total === 0 ? (
          <p className="text-sm text-muted-foreground">{t("privacy.panel.none")}</p>
        ) : (
          <EntityCountList counts={counts} />
        )}
      </CardContent>
    </Card>
  );
}
