"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Loader } from "@/components/common/Loader";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/I18nProvider";
import type { MemoryInput, MemoryKind } from "@/types/api";

export const MEMORY_KINDS: MemoryKind[] = ["fact", "preference", "person", "note"];

const schema = z.object({
  kind: z.enum(["fact", "preference", "person", "note"]),
  content: z.string().trim().min(2).max(1000),
});

export interface MemoryFormProps {
  defaultValues?: MemoryInput;
  submitting?: boolean;
  onSubmit: (values: MemoryInput) => void;
}

export function MemoryForm({ defaultValues, submitting, onSubmit }: MemoryFormProps) {
  const t = useT();
  const form = useForm<MemoryInput>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues ?? { kind: "fact", content: "" },
  });
  const contentError = form.formState.errors.content;

  return (
    <form className="flex flex-col gap-4" onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor="memory-kind">{t("memory.kind")}</Label>
        <select
          id="memory-kind"
          className="h-10 rounded-md border border-input bg-transparent px-3 text-sm"
          {...form.register("kind")}
        >
          {MEMORY_KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {t(`memory.kind.${kind}`)}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="memory-content">{t("memory.content")}</Label>
        <Textarea
          id="memory-content"
          aria-invalid={!!contentError}
          aria-describedby={contentError ? "memory-content-error" : undefined}
          {...form.register("content")}
        />
        {contentError ? (
          <p id="memory-content-error" className="text-sm text-destructive">
            {t("memory.validation.content")}
          </p>
        ) : null}
      </div>
      <Button type="submit" disabled={submitting} className="self-end">
        {submitting ? <Loader size="sm" /> : null}
        {t("common.save")}
      </Button>
    </form>
  );
}
