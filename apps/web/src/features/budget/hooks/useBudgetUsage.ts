"use client";

import { useQuery } from "@tanstack/react-query";

import { getBudgetUsage } from "../api/budget";

export function useBudgetUsage(range: "day" | "week" = "day") {
  return useQuery({
    queryKey: ["budget-usage", range],
    queryFn: () => getBudgetUsage(range),
    refetchInterval: 60_000,
  });
}
