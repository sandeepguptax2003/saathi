import { api } from "@/lib/api";
import type { PageParams, Paginated, PrivacyEvent, PrivacyPreview } from "@/types/api";

export async function listPrivacyEvents(params: PageParams = {}): Promise<Paginated<PrivacyEvent>> {
  const { data, meta } = await api.request<PrivacyEvent[]>("/privacy/events", {
    query: { cursor: params.cursor, limit: params.limit ?? 20 },
  });
  return { items: data ?? [], nextCursor: meta.nextCursor ?? null };
}

export async function previewMasking(text: string): Promise<PrivacyPreview> {
  const { data } = await api.request<PrivacyPreview>("/privacy/preview", {
    method: "POST",
    body: { text },
  });
  return data;
}
