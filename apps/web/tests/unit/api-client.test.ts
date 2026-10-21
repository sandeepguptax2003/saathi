import { describe, expect, it, vi } from "vitest";

import { buildUrl, createApiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    status: init.status ?? 200,
  });
}

describe("buildUrl", () => {
  it("prefixes /api/v1 and drops empty query values", () => {
    expect(
      buildUrl("http://api.test/", "/memories", { kind: "fact", q: "", cursor: undefined }),
    ).toBe("http://api.test/api/v1/memories?kind=fact");
  });
});

describe("createApiClient", () => {
  it("sends auth, request id and idempotency headers and unwraps the envelope", async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(
        { data: { id: "a1" }, meta: { nextCursor: "c2" } },
        { headers: { "X-Request-ID": "srv-1" } },
      ),
    );
    const client = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => "jwt-token",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });

    const result = await client.request<{ id: string }>("/pending-actions/a1/approve", {
      method: "POST",
      idempotencyKey: "key-123",
    });

    expect(result).toEqual({ data: { id: "a1" }, meta: { requestId: "srv-1", nextCursor: "c2" } });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/api/v1/pending-actions/a1/approve");
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer jwt-token");
    expect(headers["Idempotency-Key"]).toBe("key-123");
    expect(headers["X-Request-ID"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("maps the error envelope to ApiError with code, requestId and Retry-After", async () => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      fetchImpl: (async () =>
        jsonResponse(
          { error: { code: "budget_exceeded", message: "Daily cap hit", requestId: "req-9" } },
          { status: 429, headers: { "Retry-After": "30" } },
        )) as unknown as typeof fetch,
    });

    const error = await client.request("/assistant/turns").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 429,
      code: "budget_exceeded",
      message: "Daily cap hit",
      requestId: "req-9",
      retryAfterSeconds: 30,
    });
  });

  it("turns fetch failures into a retryable network_error", async () => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      fetchImpl: (async () => {
        throw new TypeError("Failed to fetch");
      }) as unknown as typeof fetch,
    });
    const error = (await client.request("/me").catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.isRetryable).toBe(true);
    expect(error.requestId).toBeTruthy();
  });

  it("falls back to a status-based code for non-JSON errors", async () => {
    const client = createApiClient({
      baseUrl: "http://api.test",
      fetchImpl: (async () =>
        new Response("gateway down", { status: 503 })) as unknown as typeof fetch,
    });
    const error = (await client.request("/me").catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("llm_unavailable");
  });
});
