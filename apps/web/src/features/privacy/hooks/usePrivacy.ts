"use client";

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import type { PageParams } from "@/types/api";

import { listPrivacyEvents, previewMasking } from "../api/privacy";

export const privacyKeys = {
  all: ["privacy-events"] as const,
  list: (params: PageParams) => [...privacyKeys.all, params] as const,
};

export function usePrivacyEvents(params: PageParams = {}) {
  return useQuery({
    queryKey: privacyKeys.list(params),
    queryFn: () => listPrivacyEvents(params),
    placeholderData: keepPreviousData,
  });
}

export function usePrivacyPreview() {
  return useMutation({ mutationFn: previewMasking });
}
