"use client";

import { PencilIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Modal } from "@/components/common/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { formatDateTime } from "@/lib/utils";
import type { Memory } from "@/types/api";

import { useDeleteMemory, useUpdateMemory } from "../hooks/useMemories";
import { MemoryForm } from "./MemoryForm";

export function MemoryItem({ memory }: { memory: Memory }) {
  const { t, bcp47 } = useI18n();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [hard, setHard] = useState(false);
  const update = useUpdateMemory();
  const remove = useDeleteMemory();

  return (
    <li className="flex items-start justify-between gap-3 rounded-xl border p-4">
      <div className="flex min-w-0 flex-col gap-1.5">
        <Badge variant="outline" className="self-start">
          {t(`memory.kind.${memory.kind}`)}
        </Badge>
        <p className="text-sm break-words">{memory.content}</p>
        <p className="text-xs text-muted-foreground">{formatDateTime(memory.updatedAt, bcp47)}</p>
      </div>
      <div className="flex shrink-0 gap-1">
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("common.edit")}
          onClick={() => setEditing(true)}
        >
          <PencilIcon aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("common.delete")}
          onClick={() => {
            setHard(false);
            setDeleting(true);
          }}
        >
          <Trash2Icon aria-hidden="true" />
        </Button>
      </div>

      <Modal open={editing} onOpenChange={setEditing} title={t("memory.edit")}>
        <MemoryForm
          defaultValues={{ kind: memory.kind, content: memory.content }}
          submitting={update.isPending}
          onSubmit={(input) =>
            update.mutate({ id: memory.id, input }, { onSuccess: () => setEditing(false) })
          }
        />
      </Modal>

      <ConfirmDialog
        open={deleting}
        onOpenChange={setDeleting}
        title={t("memory.deleteTitle")}
        description={t("memory.deleteBody")}
        confirmLabel={t("common.delete")}
        destructive
        onConfirm={() => remove.mutateAsync({ id: memory.id, hard })}
      >
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={hard} onChange={(e) => setHard(e.target.checked)} />
          {t("memory.hardDelete")}
        </label>
      </ConfirmDialog>
    </li>
  );
}
