"use client";

import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { WakingSaathi } from "@/components/common/WakingSaathi";
import { useApiWake } from "@/features/health/hooks/useApiWake";

import { AppHeader } from "./AppHeader";

export function AppShell({ children }: { children: React.ReactNode }) {
  const wake = useApiWake();
  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader apiReady={wake.status === "ready"} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
      {wake.status === "waking" || wake.status === "failed" ? (
        <WakingSaathi
          elapsedSeconds={wake.elapsed}
          failed={wake.status === "failed"}
          onRetry={wake.retry}
        />
      ) : null}
    </div>
  );
}
