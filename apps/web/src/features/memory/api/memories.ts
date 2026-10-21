import { api } from "@/lib/api";
import type { Memory, MemoryInput, MemoryKind, PageParams, Paginated } from "@/types/api";

export interface ListMemoriesParams extends PageParams {
  kind?: MemoryKind;
  /** Semantic search query. */
  q?: string;
}

export async function listMemories(params: ListMemoriesParams = {}): Promise<Paginated<Memory>> {
  const { data, meta } = await api.request<Memory[]>("/memories", {
    query: { kind: params.kind, q: params.q, cursor: params.cursor, limit: params.limit ?? 20 },
  });
  return { items: data ?? [], nextCursor: meta.nextCursor ?? null };
}

export async function createMemory(input: MemoryInput): Promise<Memory> {
  const { data } = await api.request<Memory>("/memories", { method: "POST", body: input });
  return data;
}

export async function updateMemory(id: string, input: Partial<MemoryInput>): Promise<Memory> {
  const { data } = await api.request<Memory>(`/memories/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: input,
  });
  return data;
}

/** Soft delete by default; hard=true purges ciphertext permanently. */
export async function deleteMemory(id: string, hard = false): Promise<void> {
  await api.request<void>(`/memories/${encodeURIComponent(id)}`, {
    method: "DELETE",
    query: { hard: hard || undefined },
  });
}
