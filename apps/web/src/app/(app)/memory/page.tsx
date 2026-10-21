"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { MemoryBrowser } from "@/features/memory/components/MemoryBrowser";
import { useT } from "@/lib/i18n/I18nProvider";

export default function MemoryPage() {
  const t = useT();
  return (
    <>
      <PageHeader title={t("memory.title")} subtitle={t("memory.subtitle")} />
      <MemoryBrowser />
    </>
  );
}
