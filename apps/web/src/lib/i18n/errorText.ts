import { isApiError } from "@/lib/api/errors";

import type { MessageKey } from "./dictionaries";

const CODE_KEYS: Record<string, MessageKey> = {
  network_error: "error.network_error",
  unauthorized: "error.unauthorized",
  forbidden: "error.forbidden",
  not_found: "error.not_found",
  rate_limited: "error.rate_limited",
  budget_exceeded: "error.budget_exceeded",
  upstream_error: "error.llm",
  llm_unavailable: "error.llm",
  internal_error: "common.somethingWrong",
};

type T = (key: MessageKey, vars?: Record<string, string | number>) => string;

export function errorCodeText(t: T, code: string | undefined): string {
  const key = code ? CODE_KEYS[code] : undefined;
  return t(key ?? "common.somethingWrong");
}

export function errorText(t: T, error: unknown): string {
  return errorCodeText(t, isApiError(error) ? error.code : undefined);
}
