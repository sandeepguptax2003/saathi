"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useCallback, useState } from "react";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/I18nProvider";
import { cn } from "@/lib/utils";

/**
 * Cursor pagination state. The API only returns `nextCursor`, so previous pages are
 * reached by remembering the cursors we came through (index 0 = first page = undefined).
 */
export function useCursorPagination() {
  const [stack, setStack] = useState<(string | undefined)[]>([undefined]);
  const pageIndex = stack.length - 1;
  const cursor = stack[pageIndex];

  const next = useCallback((nextCursor: string | null | undefined) => {
    if (!nextCursor) return;
    setStack((s) => [...s, nextCursor]);
  }, []);
  const previous = useCallback(() => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)), []);
  const reset = useCallback(() => setStack([undefined]), []);

  return { cursor, pageIndex, hasPrevious: pageIndex > 0, next, previous, reset };
}

export interface PaginationProps {
  pageIndex: number;
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
  isFetching?: boolean;
  className?: string;
}

export function Pagination({
  pageIndex,
  hasPrevious,
  hasNext,
  onPrevious,
  onNext,
  isFetching,
  className,
}: PaginationProps) {
  const t = useT();
  if (!hasPrevious && !hasNext) return null;
  return (
    <nav
      aria-label="Pagination"
      className={cn("flex items-center justify-between gap-2", className)}
    >
      <Button
        variant="outline"
        size="sm"
        onClick={onPrevious}
        disabled={!hasPrevious || isFetching}
      >
        <ChevronLeftIcon aria-hidden="true" />
        {t("common.previous")}
      </Button>
      <span className="text-sm text-muted-foreground" aria-live="polite">
        {t("common.page", { n: pageIndex + 1 })}
      </span>
      <Button variant="outline" size="sm" onClick={onNext} disabled={!hasNext || isFetching}>
        {t("common.next")}
        <ChevronRightIcon aria-hidden="true" />
      </Button>
    </nav>
  );
}
