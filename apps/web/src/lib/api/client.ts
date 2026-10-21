import { newId } from "@/lib/ids";

import { ApiError, apiErrorFromResponse } from "./errors";

export const API_PREFIX = "/api/v1";

export interface ApiMeta {
  nextCursor?: string | null;
  requestId?: string;
}

export interface ApiSuccess<T> {
  data: T;
  meta: ApiMeta;
}

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Required by the API on approve/reject; reuse the same key when retrying. */
  idempotencyKey?: string;
}

export interface ApiClientConfig {
  baseUrl: string;
  getAccessToken?: () => Promise<string | null>;
  fetchImpl?: typeof fetch;
}

export interface ApiClient {
  readonly baseUrl: string;
  /** Low-level call; resolves only for 2xx, otherwise throws ApiError. Path is relative to /api/v1. */
  fetch(path: string, options?: RequestOptions): Promise<Response>;
  /** Parses the success envelope {data, meta}. */
  request<T>(path: string, options?: RequestOptions): Promise<ApiSuccess<T>>;
}

export function buildUrl(
  baseUrl: string,
  path: string,
  query?: Record<string, QueryValue>,
): string {
  const url = new URL(
    `${baseUrl.replace(/\/+$/, "")}${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`,
  );
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }
  return url.toString();
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  const doFetch = config.fetchImpl ?? ((...args: Parameters<typeof fetch>) => fetch(...args));

  async function rawFetch(path: string, options: RequestOptions = {}): Promise<Response> {
    const requestId = newId();
    const headers: Record<string, string> = {
      Accept: "application/json",
      "X-Request-ID": requestId,
      ...options.headers,
    };
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;
    const token = config.getAccessToken ? await config.getAccessToken() : null;
    if (token) headers.Authorization = `Bearer ${token}`;

    let response: Response;
    try {
      response = await doFetch(buildUrl(config.baseUrl, path, options.query), {
        method: options.method ?? "GET",
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
      });
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
      throw new ApiError({
        status: 0,
        code: "network_error",
        message: "Could not reach Saathi. Check your connection and try again.",
        requestId,
      });
    }
    if (!response.ok) throw await apiErrorFromResponse(response, requestId);
    return response;
  }

  async function request<T>(path: string, options?: RequestOptions): Promise<ApiSuccess<T>> {
    const response = await rawFetch(path, options);
    const requestId = response.headers.get("x-request-id") ?? undefined;
    if (response.status === 204) return { data: undefined as T, meta: { requestId } };
    const json = (await response.json()) as Partial<ApiSuccess<T>>;
    return {
      data: json.data as T,
      meta: { requestId, ...(json.meta ?? {}) },
    };
  }

  return { baseUrl: config.baseUrl, fetch: rawFetch, request };
}
