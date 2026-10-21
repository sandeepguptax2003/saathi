"use client";

import { CheckIcon, ShieldCheckIcon, XIcon } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { newIdempotencyKey } from "@/lib/ids";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { formatDateTime } from "@/lib/utils";
import type { PendingAction } from "@/types/api";

import { useDecidePendingAction } from "../hooks/usePendingActions";

const STATUS_VARIANT = {
  pending: "secondary",
  approved: "success",
  executed: "success",
  rejected: "destructive",
  failed: "destructive",
  expired: "outline",
} as const;

export function PendingActionCard({ action }: { action: PendingAction }) {
  const { t, bcp47 } = useI18n();
  const decide = useDecidePendingAction();
  // One key per approval attempt, minted when the dialog opens and reused on retry.
  const [approveKey, setApproveKey] = useState<string | null>(null);
  const isPending = action.status === "pending";

  return (
    <Card data-testid="pending-action-card">
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon aria-hidden="true" className="size-5 text-primary" />
          <CardTitle className="text-base">{action.skill}</CardTitle>
        </div>
        <Badge variant={STATUS_VARIANT[action.status]}>
          {t(`approvals.status.${action.status}`)}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        <p className="text-sm">{action.summary}</p>
        <p className="text-xs text-muted-foreground">{formatDateTime(action.createdAt, bcp47)}</p>
      </CardContent>
      {isPending ? (
        <CardFooter>
          <Button
            size="sm"
            onClick={() => setApproveKey(newIdempotencyKey())}
            disabled={decide.isPending}
          >
            <CheckIcon aria-hidden="true" />
            {t("approvals.approve")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={decide.isPending}
            onClick={() =>
              decide.mutate({
                id: action.id,
                decision: "reject",
                idempotencyKey: newIdempotencyKey(),
              })
            }
          >
            <XIcon aria-hidden="true" />
            {t("approvals.reject")}
          </Button>
        </CardFooter>
      ) : null}
      <ConfirmDialog
        open={approveKey !== null}
        onOpenChange={(open) => !open && setApproveKey(null)}
        title={t("approvals.confirmTitle")}
        description={t("approvals.confirmBody")}
        confirmLabel={t("approvals.approve")}
        onConfirm={() =>
          decide
            .mutateAsync({
              id: action.id,
              decision: "approve",
              idempotencyKey: approveKey ?? newIdempotencyKey(),
            })
            .then(() => undefined)
        }
      >
        <blockquote className="rounded-lg border bg-muted/50 p-3 text-sm">
          {action.summary}
        </blockquote>
      </ConfirmDialog>
    </Card>
  );
}
