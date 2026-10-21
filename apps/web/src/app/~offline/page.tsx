import type { Metadata } from "next";

export const metadata: Metadata = { title: "Offline" };

export default function OfflinePage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-3 p-6 text-center">
      <span aria-hidden="true" className="text-4xl">
        🪔
      </span>
      <h1 className="text-xl font-semibold">You are offline · आप ऑफ़लाइन हैं</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Saathi needs a connection to think. Your data stays safe in the meantime.
      </p>
    </main>
  );
}
