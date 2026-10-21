"use client";

import { ShieldCheckIcon } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Pagination, useCursorPagination } from "@/components/common/Pagination";
import { ListSkeleton } from "@/components/common/Skeletons";
import { useT } from "@/lib/i18n/I18nProvider";
import type { PendingActionStatus } from "@/types/api";

import { usePendingActions } from "../hooks/usePendingActions";
import { PendingActionCard } from "./PendingActionCard";

export function PendingActionList({
  status = "pending",
  limit = 10,
  compact = false,
}: {
  status?: PendingActionStatus;
  limit?: number;
  compact?: boolean;
}) {
  const t = useT();
  const pager = useCursorPagination();
  const query = usePendingActions({ status, cursor: pager.cursor, limit });

  if (query.isPending) return <ListSkeleton rows={compact ? 1 : 3} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const items = query.data.items;
  if (items.length === 0) {
    if (compact) return null;
    return (
      <EmptyState
        icon={ShieldCheckIcon}
        title={t("approvals.empty.title")}
        description={t("approvals.empty.body")}
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {items.map((action) => (
        <PendingActionCard key={action.id} action={action} />
      ))}
      {compact ? null : (
        <Pagination
          pageIndex={pager.pageIndex}
          hasPrevious={pager.hasPrevious}
          hasNext={!!query.data.nextCursor}
          onPrevious={pager.previous}
          onNext={() => pager.next(query.data.nextCursor)}
          isFetching={query.isFetching}
        />
      )}
    </div>
  );
}
