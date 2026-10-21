"use client";

import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { PageHeader } from "@/components/layout/PageHeader";
import { BudgetMeter } from "@/features/budget/components/BudgetMeter";
import { PrivacyEventList } from "@/features/privacy/components/PrivacyEventList";
import { PrivacyPreviewForm } from "@/features/privacy/components/PrivacyPreviewForm";
import { useT } from "@/lib/i18n/I18nProvider";

export default function PrivacyPage() {
  const t = useT();
  return (
    <>
      <PageHeader title={t("privacy.title")} subtitle={t("landing.privacy.mask")} />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="flex flex-col gap-6">
          <PrivacyPreviewForm />
          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold">{t("privacy.events.title")}</h2>
            <PrivacyEventList />
          </section>
        </div>
        <ErrorBoundary>
          <BudgetMeter />
        </ErrorBoundary>
      </div>
    </>
  );
}
