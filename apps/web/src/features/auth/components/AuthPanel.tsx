"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LogOutIcon, MailIcon } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Loader } from "@/components/common/Loader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useT } from "@/lib/i18n/I18nProvider";

import { useAuthActions } from "../hooks/useAuthActions";
import { useSession } from "../hooks/useSession";

const emailSchema = z.object({ email: z.email() });

export function AuthPanel() {
  const t = useT();
  const { user, loading } = useSession();
  const actions = useAuthActions();
  const form = useForm<{ email: string }>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  const run = (fn: () => Promise<void>, success?: string) => async () => {
    try {
      await fn();
      if (success) toast.success(success);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t("common.somethingWrong"));
    }
  };

  if (loading) return <Loader showLabel label={t("common.loading")} />;

  if (user) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">
          {user.is_anonymous
            ? t("auth.anonymous")
            : t("auth.signedInAs", { who: user.email ?? user.id })}
        </p>
        <Button variant="outline" onClick={run(actions.signOut)}>
          <LogOutIcon aria-hidden="true" />
          {t("auth.signOut")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">{t("auth.signedOut")}</p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={run(actions.signInWithGoogle)}>{t("auth.google")}</Button>
        <Button variant="outline" onClick={run(actions.startDemo)}>
          {t("auth.demo")}
        </Button>
      </div>
      <form
        className="flex flex-col gap-2 sm:flex-row sm:items-end"
        noValidate
        onSubmit={form.handleSubmit(({ email }) =>
          run(() => actions.sendMagicLink(email), t("auth.magicLinkSent"))(),
        )}
      >
        <div className="flex flex-1 flex-col gap-2">
          <Label htmlFor="auth-email">{t("auth.email")}</Label>
          <Input
            id="auth-email"
            type="email"
            autoComplete="email"
            aria-invalid={!!form.formState.errors.email}
            {...form.register("email")}
          />
        </div>
        <Button type="submit" variant="secondary" disabled={form.formState.isSubmitting}>
          <MailIcon aria-hidden="true" />
          {t("auth.magicLink")}
        </Button>
      </form>
    </div>
  );
}
