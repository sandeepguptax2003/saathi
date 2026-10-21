"use client";

import { SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Loader } from "@/components/common/Loader";
import { Button, type ButtonProps } from "@/components/ui/button";
import { useT } from "@/lib/i18n/I18nProvider";

import { useAuthActions } from "../hooks/useAuthActions";

export function TryDemoButton(props: Omit<ButtonProps, "onClick">) {
  const t = useT();
  const router = useRouter();
  const { startDemo } = useAuthActions();
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    try {
      await startDemo();
    } catch {
      toast.warning(t("auth.demoFailed"));
    } finally {
      setBusy(false);
      router.push("/console");
    }
  }

  return (
    <Button size="lg" onClick={handleClick} disabled={busy} {...props}>
      {busy ? (
        <Loader size="sm" label={t("auth.demoStarting")} />
      ) : (
        <SparklesIcon aria-hidden="true" />
      )}
      {t("landing.cta.demo")}
    </Button>
  );
}
