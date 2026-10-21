"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useReducer, useRef } from "react";

import { isApiError } from "@/lib/api/errors";
import { newId } from "@/lib/ids";
import type { EntityCounts, InputMode, Locale, TurnEvent, TurnUsage } from "@/types/api";

import { streamAssistantTurn } from "../api/turns";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  status: "streaming" | "done" | "error";
  model?: string;
  errorCode?: string;
  requestId?: string;
}

export interface InlinePendingAction {
  id: string;
  summary: string;
}

export interface TurnState {
  conversationId?: string;
  messages: ChatMessage[];
  entityCounts: EntityCounts | null;
  pendingActions: InlinePendingAction[];
  activeTool: string | null;
  isStreaming: boolean;
  lastUsage?: TurnUsage;
}

type Action =
  | { type: "start"; userId: string; assistantId: string; text: string }
  | { type: "event"; assistantId: string; event: TurnEvent }
  | { type: "fail"; assistantId: string; message: string; code?: string; requestId?: string }
  | { type: "finish"; assistantId: string };

export const initialTurnState: TurnState = {
  messages: [],
  entityCounts: null,
  pendingActions: [],
  activeTool: null,
  isStreaming: false,
};

function patchMessage(
  state: TurnState,
  id: string,
  patch: (m: ChatMessage) => ChatMessage,
): TurnState {
  return { ...state, messages: state.messages.map((m) => (m.id === id ? patch(m) : m)) };
}

export function turnReducer(state: TurnState, action: Action): TurnState {
  switch (action.type) {
    case "start":
      return {
        ...state,
        isStreaming: true,
        activeTool: null,
        entityCounts: null,
        messages: [
          ...state.messages,
          { id: action.userId, role: "user", text: action.text, status: "done" },
          { id: action.assistantId, role: "assistant", text: "", status: "streaming" },
        ],
      };
    case "event": {
      const { event, assistantId } = action;
      switch (event.type) {
        case "meta":
          return patchMessage(
            { ...state, conversationId: event.conversationId },
            assistantId,
            (m) => ({ ...m, model: event.model }),
          );
        case "privacy":
          return { ...state, entityCounts: event.entityCounts };
        case "token":
          return patchMessage(state, assistantId, (m) => ({ ...m, text: m.text + event.delta }));
        case "tool":
          return { ...state, activeTool: event.status === "done" ? null : event.skill };
        case "pending_action":
          return state.pendingActions.some((p) => p.id === event.id)
            ? state
            : {
                ...state,
                pendingActions: [...state.pendingActions, { id: event.id, summary: event.summary }],
              };
        case "done":
          return patchMessage(
            { ...state, isStreaming: false, activeTool: null, lastUsage: event.usage },
            assistantId,
            (m) => ({ ...m, status: "done", model: m.model ?? event.usage?.model }),
          );
        case "error":
          return patchMessage(
            { ...state, isStreaming: false, activeTool: null },
            assistantId,
            (m) => ({
              ...m,
              status: "error",
              text: m.text || event.message,
              errorCode: event.code,
              requestId: event.requestId,
            }),
          );
      }
      return state;
    }
    case "fail":
      return patchMessage(
        { ...state, isStreaming: false, activeTool: null },
        action.assistantId,
        (m) => ({
          ...m,
          status: "error",
          text: m.text || action.message,
          errorCode: action.code,
          requestId: action.requestId,
        }),
      );
    case "finish":
      return patchMessage(
        { ...state, isStreaming: false, activeTool: null },
        action.assistantId,
        (m) => (m.status === "streaming" ? { ...m, status: "done" } : m),
      );
  }
}

export interface UseAssistantTurnOptions {
  locale: Locale;
  /** Called with the full assistant reply once streaming completes (for TTS). */
  onReply?: (text: string) => void;
}

export function useAssistantTurn({ locale, onReply }: UseAssistantTurnOptions) {
  const [state, dispatch] = useReducer(turnReducer, initialTurnState);
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const conversationRef = useRef<string | undefined>(undefined);
  const onReplyRef = useRef(onReply);
  onReplyRef.current = onReply;

  useEffect(() => {
    conversationRef.current = state.conversationId;
  }, [state.conversationId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(
    async (rawText: string, inputMode: InputMode) => {
      const text = rawText.trim();
      if (!text) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const assistantId = newId();
      dispatch({ type: "start", userId: newId(), assistantId, text });

      let reply = "";
      let failed = false;
      try {
        for await (const event of streamAssistantTurn(
          { conversationId: conversationRef.current, text, locale, inputMode },
          { signal: controller.signal },
        )) {
          if (event.type === "token") reply += event.delta;
          if (event.type === "error") failed = true;
          dispatch({ type: "event", assistantId, event });
        }
        dispatch({ type: "finish", assistantId });
        if (!failed && reply) onReplyRef.current?.(reply);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          dispatch({ type: "finish", assistantId });
          return;
        }
        dispatch({
          type: "fail",
          assistantId,
          message: error instanceof Error ? error.message : "Something went wrong",
          code: isApiError(error) ? error.code : undefined,
          requestId: isApiError(error) ? error.requestId : undefined,
        });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        void queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
        void queryClient.invalidateQueries({ queryKey: ["privacy-events"] });
        void queryClient.invalidateQueries({ queryKey: ["budget-usage"] });
      }
    },
    [locale, queryClient],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send, stop };
}
