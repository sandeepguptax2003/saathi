"use client";

import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { PendingActionList } from "@/features/approvals/components/PendingActionList";
import { useT } from "@/lib/i18n/I18nProvider";
import type { PendingActionStatus } from "@/types/api";

const TABS: PendingActionStatus[] = ["pending", "approved", "executed", "rejected", "expired"];

export default function ApprovalsPage() {
  const t = useT();
  const [status, setStatus] = useState<PendingActionStatus>("pending");
  return (
    <>
      <PageHeader title={t("approvals.title")} subtitle={t("approvals.subtitle")} />
      <div role="tablist" aria-label={t("approvals.title")} className="mb-4 flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <Button
            key={tab}
            role="tab"
            aria-selected={status === tab}
            size="sm"
            variant={status === tab ? "default" : "outline"}
            onClick={() => setStatus(tab)}
          >
            {t(`approvals.status.${tab}`)}
          </Button>
        ))}
      </div>
      <PendingActionList key={status} status={status} />
    </>
  );
}
