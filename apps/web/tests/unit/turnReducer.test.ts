import { describe, expect, it } from "vitest";

import { initialTurnState, turnReducer } from "@/features/chat/hooks/useAssistantTurn";

describe("turnReducer", () => {
  it("streams tokens into the assistant message and records privacy + pending actions", () => {
    let s = turnReducer(initialTurnState, {
      type: "start",
      userId: "u1",
      assistantId: "a1",
      text: "hi",
    });
    s = turnReducer(s, {
      type: "event",
      assistantId: "a1",
      event: { type: "meta", conversationId: "c1", model: "nano" },
    });
    s = turnReducer(s, {
      type: "event",
      assistantId: "a1",
      event: { type: "privacy", entityCounts: { phone: 2 } },
    });
    s = turnReducer(s, {
      type: "event",
      assistantId: "a1",
      event: { type: "token", delta: "Nam" },
    });
    s = turnReducer(s, {
      type: "event",
      assistantId: "a1",
      event: { type: "token", delta: "aste" },
    });
    s = turnReducer(s, {
      type: "event",
      assistantId: "a1",
      event: { type: "pending_action", id: "p1", summary: "Pay ₹500" },
    });
    s = turnReducer(s, { type: "event", assistantId: "a1", event: { type: "done" } });

    expect(s.conversationId).toBe("c1");
    expect(s.entityCounts).toEqual({ phone: 2 });
    expect(s.pendingActions).toEqual([{ id: "p1", summary: "Pay ₹500" }]);
    expect(s.isStreaming).toBe(false);
    expect(s.messages[1]).toMatchObject({
      role: "assistant",
      text: "Namaste",
      status: "done",
      model: "nano",
    });
  });

  it("marks the assistant message as errored with the request id", () => {
    let s = turnReducer(initialTurnState, {
      type: "start",
      userId: "u1",
      assistantId: "a1",
      text: "hi",
    });
    s = turnReducer(s, {
      type: "fail",
      assistantId: "a1",
      message: "Budget hit",
      code: "budget_exceeded",
      requestId: "r1",
    });
    expect(s.messages[1]).toMatchObject({ status: "error", text: "Budget hit", requestId: "r1" });
    expect(s.isStreaming).toBe(false);
  });
});
