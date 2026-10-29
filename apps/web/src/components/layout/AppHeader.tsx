"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { LocaleToggle } from "@/components/common/LocaleToggle";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { usePendingActions } from "@/features/approvals/hooks/usePendingActions";
import type { MessageKey } from "@/lib/i18n/dictionaries";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: MessageKey }[] = [
  { href: "/console", label: "nav.console" },
  { href: "/memory", label: "nav.memory" },
  { href: "/approvals", label: "nav.approvals" },
  { href: "/privacy", label: "nav.privacy" },
  { href: "/settings", label: "nav.settings" },
];

export function AppHeader({ apiReady }: { apiReady: boolean }) {
  const t = useT();
  const pathname = usePathname();
  const pending = usePendingActions({ status: "pending", limit: 20 }, apiReady);
  const pendingCount = pending.data?.items.length ?? 0;

  return (
    <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 md:h-14 md:flex-nowrap md:py-0">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span aria-hidden="true">🪔</span>
          {t("app.name")}
        </Link>
        <nav
          aria-label="Main"
          className="order-last -mx-1 flex w-full flex-wrap gap-1 md:order-none md:w-auto md:flex-1 md:flex-nowrap"
        >
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition-colors hover:bg-muted",
                  active ? "bg-muted font-medium" : "text-muted-foreground",
                )}
              >
                {t(item.label)}
                {item.href === "/approvals" && pendingCount > 0 ? (
                  <span className="ml-1.5 inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] text-primary-foreground">
                    {pendingCount}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <LocaleToggle />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
