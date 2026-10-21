"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/I18nProvider";
import type { MeUpdate } from "@/types/api";

import { getMe, resetDemo, updateMe } from "../api/me";

export const meKey = ["me"] as const;

export function useMe(enabled = true) {
  return useQuery({ queryKey: meKey, queryFn: getMe, enabled });
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  const t = useT();
  return useMutation({
    mutationFn: (input: MeUpdate) => updateMe(input),
    onSuccess: (me) => {
      queryClient.setQueryData(meKey, me);
      toast.success(t("settings.saved"));
    },
    onError: (error) => toast.error(error.message),
  });
}

export function useResetDemo() {
  const queryClient = useQueryClient();
  const t = useT();
  return useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      toast.success(t("settings.demo.done"));
      void queryClient.invalidateQueries();
    },
    onError: (error) => toast.error(error.message),
  });
}
