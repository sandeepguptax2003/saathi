"use client";

import { BrainIcon, PlusIcon } from "lucide-react";
import { useDeferredValue, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { Pagination, useCursorPagination } from "@/components/common/Pagination";
import { ListSkeleton } from "@/components/common/Skeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";
import type { MemoryKind } from "@/types/api";

import { useCreateMemory, useMemories } from "../hooks/useMemories";
import { MEMORY_KINDS, MemoryForm } from "./MemoryForm";
import { MemoryItem } from "./MemoryItem";

export function MemoryBrowser() {
  const t = useT();
  const [kind, setKind] = useState<MemoryKind | undefined>(undefined);
  const [search, setSearch] = useState("");
  const q = useDeferredValue(search.trim());
  const [adding, setAdding] = useState(false);
  const pager = useCursorPagination();
  const query = useMemories({ kind, q: q || undefined, cursor: pager.cursor });
  const create = useCreateMemory();

  const filterButton = (value: MemoryKind | undefined, label: string) => (
    <Button
      key={label}
      size="sm"
      variant={kind === value ? "default" : "outline"}
      aria-pressed={kind === value}
      onClick={() => {
        setKind(value);
        pager.reset();
      }}
    >
      {label}
    </Button>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Input
          type="search"
          aria-label={t("memory.search")}
          placeholder={t("memory.search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            pager.reset();
          }}
          className="sm:max-w-xs"
        />
        <Button onClick={() => setAdding(true)}>
          <PlusIcon aria-hidden="true" />
          {t("memory.add")}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("memory.kind")}>
        {filterButton(undefined, t("memory.kind.all"))}
        {MEMORY_KINDS.map((k) => filterButton(k, t(`memory.kind.${k}`)))}
      </div>

      {query.isPending ? (
        <ListSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.data.items.length === 0 ? (
        <EmptyState
          icon={BrainIcon}
          title={t("memory.empty.title")}
          description={t("memory.empty.body")}
        />
      ) : (
        <>
          <ul className={cn("flex flex-col gap-2", query.isFetching && "opacity-70")}>
            {query.data.items.map((memory) => (
              <MemoryItem key={memory.id} memory={memory} />
            ))}
          </ul>
          <Pagination
            pageIndex={pager.pageIndex}
            hasPrevious={pager.hasPrevious}
            hasNext={!!query.data.nextCursor}
            onPrevious={pager.previous}
            onNext={() => pager.next(query.data.nextCursor)}
            isFetching={query.isFetching}
          />
        </>
      )}

      <Modal open={adding} onOpenChange={setAdding} title={t("memory.add")}>
        <MemoryForm
          submitting={create.isPending}
          onSubmit={(input) => create.mutate(input, { onSuccess: () => setAdding(false) })}
        />
      </Modal>
    </div>
  );
}
