"use client";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Pagination, useCursorPagination } from "@/components/common/Pagination";
import { ListSkeleton } from "@/components/common/Skeletons";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { formatDateTime } from "@/lib/utils";

import { usePrivacyEvents } from "../hooks/usePrivacy";
import { EntityCountList } from "./EntityCountList";

export function PrivacyEventList() {
  const { t, bcp47 } = useI18n();
  const pager = useCursorPagination();
  const query = usePrivacyEvents({ cursor: pager.cursor });

  if (query.isPending) return <ListSkeleton rows={3} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (query.data.items.length === 0) return <EmptyState title={t("privacy.events.empty")} />;
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2">
        {query.data.items.map((event) => (
          <li key={event.id} className="flex flex-col gap-2 rounded-xl border p-4">
            <span className="text-xs text-muted-foreground">
              {formatDateTime(event.createdAt, bcp47)}
            </span>
            {Object.values(event.entityCounts).some((n) => n > 0) ? (
              <EntityCountList counts={event.entityCounts} />
            ) : (
              <span className="text-sm text-muted-foreground">{t("privacy.events.none")}</span>
            )}
          </li>
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
    </div>
  );
}
