"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/I18nProvider";
import type { Memory, MemoryInput, Paginated } from "@/types/api";

import {
  createMemory,
  deleteMemory,
  listMemories,
  updateMemory,
  type ListMemoriesParams,
} from "../api/memories";

export const memoryKeys = {
  all: ["memories"] as const,
  list: (params: ListMemoriesParams) => [...memoryKeys.all, params] as const,
};

export function useMemories(params: ListMemoriesParams) {
  return useQuery({
    queryKey: memoryKeys.list(params),
    queryFn: () => listMemories(params),
    placeholderData: keepPreviousData,
  });
}

function useToastError() {
  const t = useT();
  return (error: Error) => toast.error(error.message || t("common.somethingWrong"));
}

export function useCreateMemory() {
  const queryClient = useQueryClient();
  const t = useT();
  const onError = useToastError();
  return useMutation({
    mutationFn: (input: MemoryInput) => createMemory(input),
    onSuccess: () => toast.success(t("memory.saved")),
    onError,
    onSettled: () => queryClient.invalidateQueries({ queryKey: memoryKeys.all }),
  });
}

export function useUpdateMemory() {
  const queryClient = useQueryClient();
  const t = useT();
  const onError = useToastError();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<MemoryInput> }) =>
      updateMemory(id, input),
    onSuccess: () => toast.success(t("memory.saved")),
    onError,
    onSettled: () => queryClient.invalidateQueries({ queryKey: memoryKeys.all }),
  });
}

export function useDeleteMemory() {
  const queryClient = useQueryClient();
  const t = useT();
  const onError = useToastError();
  return useMutation({
    mutationFn: ({ id, hard }: { id: string; hard: boolean }) => deleteMemory(id, hard),
    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({ queryKey: memoryKeys.all });
      const snapshot = queryClient.getQueriesData<Paginated<Memory>>({ queryKey: memoryKeys.all });
      queryClient.setQueriesData<Paginated<Memory>>({ queryKey: memoryKeys.all }, (old) =>
        old ? { ...old, items: old.items.filter((m) => m.id !== id) } : old,
      );
      return { snapshot };
    },
    onError: (error, _vars, context) => {
      context?.snapshot.forEach(([key, data]) => queryClient.setQueryData(key, data));
      onError(error);
    },
    onSuccess: () => toast.success(t("memory.deleted")),
    onSettled: () => queryClient.invalidateQueries({ queryKey: memoryKeys.all }),
  });
}
