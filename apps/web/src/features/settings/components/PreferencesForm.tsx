"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/ErrorState";
import { Loader } from "@/components/common/Loader";
import { CardSkeleton } from "@/components/common/Skeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isApiError } from "@/lib/api/errors";
import { useT } from "@/lib/i18n/I18nProvider";
import type { Me } from "@/types/api";

import { useMe, useUpdateMe } from "../hooks/useMe";

const schema = z.object({
  displayName: z.string().trim().max(60),
  locale: z.enum(["hi-IN", "en-IN"]),
  timezone: z.string().trim().min(1).max(64),
  dailyBudgetUsd: z.number().min(0).max(5),
});
type FormValues = z.infer<typeof schema>;

function Form({ me }: { me: Me }) {
  const t = useT();
  const update = useUpdateMe();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      displayName: me.displayName ?? "",
      locale: me.locale,
      timezone: me.timezone,
      dailyBudgetUsd: me.dailyBudgetUsd,
    },
  });
  const errors = form.formState.errors;

  return (
    <form
      className="grid gap-4 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit((values) =>
        update.mutate({ ...values, displayName: values.displayName || null }),
      )}
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="displayName">{t("settings.displayName")}</Label>
        <Input id="displayName" {...form.register("displayName")} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="locale">{t("settings.speechLocale")}</Label>
        <select
          id="locale"
          className="h-10 rounded-md border border-input bg-transparent px-3 text-sm"
          {...form.register("locale")}
        >
          <option value="hi-IN">हिंदी (hi-IN)</option>
          <option value="en-IN">English (en-IN)</option>
        </select>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="timezone">{t("settings.timezone")}</Label>
        <Input id="timezone" {...form.register("timezone")} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="dailyBudgetUsd">{t("settings.dailyBudget")}</Label>
        <Input
          id="dailyBudgetUsd"
          type="number"
          step="0.1"
          min={0}
          max={5}
          aria-invalid={!!errors.dailyBudgetUsd}
          {...form.register("dailyBudgetUsd", { valueAsNumber: true })}
        />
        {errors.dailyBudgetUsd ? (
          <p className="text-sm text-destructive">{t("settings.validation.budget")}</p>
        ) : null}
      </div>
      <Button
        type="submit"
        className="self-end sm:col-span-2 sm:justify-self-end"
        disabled={update.isPending}
      >
        {update.isPending ? <Loader size="sm" /> : null}
        {t("common.save")}
      </Button>
    </form>
  );
}

export function PreferencesForm({ signedIn }: { signedIn: boolean }) {
  const t = useT();
  const query = useMe(signedIn);
  if (!signedIn)
    return <p className="text-sm text-muted-foreground">{t("settings.signInFirst")}</p>;
  if (query.isPending) return <CardSkeleton />;
  if (query.isError) {
    if (isApiError(query.error) && query.error.status === 401)
      return <p className="text-sm text-muted-foreground">{t("settings.signInFirst")}</p>;
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  }
  return <Form me={query.data} />;
}
