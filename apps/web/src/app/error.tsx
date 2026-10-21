"use client";

import { ErrorState } from "@/components/common/ErrorState";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-xl items-center p-6">
      <ErrorState error={error} onRetry={reset} className="w-full" />
    </main>
  );
}
