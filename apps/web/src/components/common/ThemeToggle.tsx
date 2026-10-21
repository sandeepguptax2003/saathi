"use client";

import { MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/I18nProvider";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useT();
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={t("theme.toggle")}
      title={t("theme.toggle")}
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      <SunIcon aria-hidden="true" className="hidden dark:block" />
      <MoonIcon aria-hidden="true" className="dark:hidden" />
    </Button>
  );
}
