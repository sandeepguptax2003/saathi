"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Loader } from "@/components/common/Loader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { isApiError } from "@/lib/api/errors";
import { errorText } from "@/lib/i18n/errorText";
import { useT } from "@/lib/i18n/I18nProvider";

import { usePrivacyPreview } from "../hooks/usePrivacy";
import { EntityCountList } from "./EntityCountList";

const schema = z.object({ text: z.string().trim().min(1).max(2000) });
type FormValues = z.infer<typeof schema>;

export function PrivacyPreviewForm() {
  const t = useT();
  const preview = usePrivacyPreview();
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { text: "" } });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("privacy.preview.title")}</CardTitle>
        <CardDescription>{t("privacy.preview.body")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form
          className="flex flex-col gap-3"
          onSubmit={form.handleSubmit((values) => preview.mutate(values.text))}
        >
          <Label htmlFor="privacy-preview-text" className="sr-only">
            {t("privacy.preview.title")}
          </Label>
          <Textarea
            id="privacy-preview-text"
            placeholder="Mera number 98xxxxxx10 hai, UPI san@okaxis pe 500 bhejo"
            {...form.register("text")}
          />
          <Button type="submit" className="self-start" disabled={preview.isPending}>
            {preview.isPending ? <Loader size="sm" /> : null}
            {t("privacy.preview.run")}
          </Button>
        </form>
        {preview.isError ? (
          <p role="alert" className="text-sm text-destructive">
            {errorText(t, preview.error)}
            {isApiError(preview.error) && preview.error.requestId
              ? ` · ${t("common.requestId", { id: preview.error.requestId })}`
              : null}
          </p>
        ) : null}
        {preview.data ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">{t("privacy.preview.result")}</p>
            <pre className="rounded-lg border bg-muted/50 p-3 text-sm whitespace-pre-wrap">
              {preview.data.maskedText}
            </pre>
            <EntityCountList counts={preview.data.entityCounts} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
