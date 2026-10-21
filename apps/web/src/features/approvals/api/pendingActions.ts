import { api } from "@/lib/api";
import type { ApiClient } from "@/lib/api/client";
import type { PageParams, Paginated, PendingAction, PendingActionStatus } from "@/types/api";

export type Decision = "approve" | "reject";

export interface ListPendingActionsParams extends PageParams {
  status?: PendingActionStatus;
}

export async function listPendingActions(
  params: ListPendingActionsParams = {},
  client: ApiClient = api,
): Promise<Paginated<PendingAction>> {
  const { data, meta } = await client.request<PendingAction[]>("/pending-actions", {
    query: { status: params.status, cursor: params.cursor, limit: params.limit ?? 20 },
  });
  return { items: data ?? [], nextCursor: meta.nextCursor ?? null };
}

/** Idempotency-Key is required by the API; pass the same key when retrying one decision. */
export async function decidePendingAction(
  id: string,
  decision: Decision,
  idempotencyKey: string,
  client: ApiClient = api,
): Promise<PendingAction> {
  const { data } = await client.request<PendingAction>(
    `/pending-actions/${encodeURIComponent(id)}/${decision}`,
    { method: "POST", idempotencyKey },
  );
  return data;
}
