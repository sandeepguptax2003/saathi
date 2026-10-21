"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { isApiError } from "@/lib/api/errors";
import { useT } from "@/lib/i18n/I18nProvider";
import type { Paginated, PendingAction } from "@/types/api";

import {
  decidePendingAction,
  listPendingActions,
  type Decision,
  type ListPendingActionsParams,
} from "../api/pendingActions";

export const pendingActionKeys = {
  all: ["pending-actions"] as const,
  list: (params: ListPendingActionsParams) => [...pendingActionKeys.all, "list", params] as const,
};

export function usePendingActions(params: ListPendingActionsParams = {}, enabled = true) {
  return useQuery({
    queryKey: pendingActionKeys.list(params),
    queryFn: () => listPendingActions(params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export interface DecideVariables {
  id: string;
  decision: Decision;
  /** Created once per user tap so retries replay instead of double-executing. */
  idempotencyKey: string;
}

export function useDecidePendingAction() {
  const queryClient = useQueryClient();
  const t = useT();
  return useMutation({
    mutationFn: ({ id, decision, idempotencyKey }: DecideVariables) =>
      decidePendingAction(id, decision, idempotencyKey),
    // Network blips / 5xx are safe to retry because the key is reused.
    retry: (count, error) => count < 2 && isApiError(error) && error.isRetryable,
    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({ queryKey: pendingActionKeys.all });
      const snapshot = queryClient.getQueriesData<Paginated<PendingAction>>({
        queryKey: pendingActionKeys.all,
      });
      queryClient.setQueriesData<Paginated<PendingAction>>(
        { queryKey: pendingActionKeys.all },
        (old) =>
          old
            ? { ...old, items: old.items.filter((a) => a.id !== id || a.status !== "pending") }
            : old,
      );
      return { snapshot };
    },
    onError: (error, _vars, context) => {
      context?.snapshot.forEach(([key, data]) => queryClient.setQueryData(key, data));
      if (isApiError(error) && error.code === "conflict") toast.info(t("approvals.alreadyDecided"));
      else
        toast.error(error instanceof Error ? error.message : t("common.somethingWrong"), {
          description:
            isApiError(error) && error.requestId
              ? t("common.requestId", { id: error.requestId })
              : undefined,
        });
    },
    onSuccess: (_data, { decision }) => {
      toast.success(decision === "approve" ? t("approvals.approved") : t("approvals.rejected"));
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: pendingActionKeys.all }),
  });
}
