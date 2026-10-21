import { describe, expect, it } from "vitest";

import { readSSE, type SSEMessage } from "@/lib/api/sse";
import { toTurnEvent } from "@/features/chat/api/turns";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<SSEMessage[]> {
  const out: SSEMessage[] = [];
  for await (const m of readSSE(stream)) out.push(m);
  return out;
}

describe("readSSE", () => {
  it("parses events split across chunk boundaries", async () => {
    const messages = await collect(
      streamOf([
        "event: tok",
        'en\ndata: {"delta":"Nam',
        'aste"}\n',
        "\nevent: done\ndata: {}\n\n",
      ]),
    );
    expect(messages).toEqual([
      { event: "token", data: '{"delta":"Namaste"}', id: undefined },
      { event: "done", data: "{}", id: undefined },
    ]);
  });

  it("handles CRLF, comments, multi-line data and a final event without a blank line", async () => {
    const messages = await collect(
      streamOf([
        ": keep-alive\r\n\r\nid: 7\r\ndata: line1\r\ndata: line2\r\n\r\nevent: done\ndata: {}",
      ]),
    );
    expect(messages).toEqual([
      { event: "message", data: "line1\nline2", id: "7" },
      { event: "done", data: "{}", id: undefined },
    ]);
  });
});

describe("toTurnEvent", () => {
  it("maps known events and drops unknown ones", () => {
    expect(toTurnEvent({ event: "privacy", data: '{"entityCounts":{"phone":1}}' })).toEqual({
      type: "privacy",
      entityCounts: { phone: 1 },
    });
    expect(toTurnEvent({ event: "ping", data: "{}" })).toBeNull();
  });

  it("tolerates raw-text token deltas", () => {
    expect(toTurnEvent({ event: "token", data: "hello" })).toEqual({
      type: "token",
      delta: "hello",
    });
  });
});
