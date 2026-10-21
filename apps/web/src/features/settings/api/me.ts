import { api } from "@/lib/api";
import type { Me, MeUpdate } from "@/types/api";

export async function getMe(): Promise<Me> {
  const { data } = await api.request<Me>("/me");
  return data;
}

export async function updateMe(input: MeUpdate): Promise<Me> {
  const { data } = await api.request<Me>("/me", { method: "PATCH", body: input });
  return data;
}

export async function resetDemo(): Promise<void> {
  await api.request<void>("/demo/reset", { method: "POST" });
}
