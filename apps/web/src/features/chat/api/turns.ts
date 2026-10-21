import { api } from "@/lib/api";
import type { ApiClient } from "@/lib/api/client";
import { ApiError } from "@/lib/api/errors";
import { readSSE, type SSEMessage } from "@/lib/api/sse";
import type { AssistantTurnRequest, TurnEvent, TurnEventType } from "@/types/api";

const EVENT_TYPES: ReadonlySet<TurnEventType> = new Set([
  "meta",
  "privacy",
  "token",
  "tool",
  "pending_action",
  "done",
  "error",
]);

export function toTurnEvent(message: SSEMessage): TurnEvent | null {
  if (!EVENT_TYPES.has(message.event as TurnEventType)) return null;
  let payload: unknown;
  try {
    payload = message.data ? JSON.parse(message.data) : {};
  } catch {
    // Tolerate a server that streams raw text deltas.
    return message.event === "token" ? { type: "token", delta: message.data } : null;
  }
  if (typeof payload !== "object" || payload === null) return null;
  return { ...(payload as object), type: message.event } as TurnEvent;
}

/**
 * POST /api/v1/assistant/turns and yield typed SSE events as they arrive.
 * HTTP errors before the stream starts throw ApiError (error envelope);
 * errors after it starts arrive as an `error` event.
 */
export async function* streamAssistantTurn(
  request: AssistantTurnRequest,
  options: { signal?: AbortSignal; client?: ApiClient } = {},
): AsyncGenerator<TurnEvent> {
  const client = options.client ?? api;
  const response = await client.fetch("/assistant/turns", {
    method: "POST",
    body: request,
    headers: { Accept: "text/event-stream" },
    signal: options.signal,
  });
  if (!response.body) {
    throw new ApiError({
      status: response.status,
      code: "upstream_error",
      message: "Empty response stream",
      requestId: response.headers.get("x-request-id") ?? undefined,
    });
  }
  for await (const message of readSSE(response.body)) {
    const event = toTurnEvent(message);
    if (event) yield event;
  }
}
