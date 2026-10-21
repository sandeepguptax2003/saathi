import { api } from "@/lib/api";
import type { BudgetUsage } from "@/types/api";

export async function getBudgetUsage(range: "day" | "week" = "day"): Promise<BudgetUsage> {
  const { data } = await api.request<BudgetUsage>("/budget/usage", { query: { range } });
  return data;
}
