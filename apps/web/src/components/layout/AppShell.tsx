"use client";

import { useEffect, useState } from "react";

import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { useAuthActions } from "@/features/auth/hooks/useAuthActions";
import { useSession } from "@/features/auth/hooks/useSession";
import { useApiWake } from "@/features/health/hooks/useApiWake";
import { useT } from "@/lib/i18n/I18nProvider";

import { AppHeader } from "./AppHeader";

export function AppShell({ children }: { children: React.ReactNode }) {
  const wake = useApiWake();
  const t = useT();
  const { session, loading } = useSession();
  const { startDemo } = useAuthActions();
  const [demoFailed, setDemoFailed] = useState(false);

  useEffect(() => {
    if (loading || session || demoFailed) return;
    startDemo().catch(() => setDemoFailed(true));
  }, [loading, session, demoFailed, startDemo]);

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader apiReady={wake.status === "ready"} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        {session ? (
          <ErrorBoundary>{children}</ErrorBoundary>
        ) : demoFailed ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-sm text-muted-foreground">{t("auth.demoFailed")}</p>
            <Button variant="outline" onClick={() => setDemoFailed(false)}>
              {t("common.retry")}
            </Button>
          </div>
        ) : null}
      </main>
    </div>
  );
}
