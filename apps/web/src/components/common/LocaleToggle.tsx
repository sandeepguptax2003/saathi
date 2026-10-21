"use client";

import { LanguagesIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/I18nProvider";

export function LocaleToggle() {
  const { t, toggleLocale } = useI18n();
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleLocale}
      aria-label={t("locale.label")}
      title={t("locale.label")}
    >
      <LanguagesIcon aria-hidden="true" />
      {t("locale.toggle")}
    </Button>
  );
}
