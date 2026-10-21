/**
 * PLACEHOLDER domain types mirroring docs/api-contract.md (v0.1).
 * Source of truth is the API's /openapi.json: run `pnpm gen:types` to write
 * src/types/api.generated.ts, then re-point these aliases at
 * `components["schemas"][...]` from that file.
 */

export type Locale = "hi-IN" | "en-IN";
export type InputMode = "voice" | "text";

export interface Paginated<T> {
  items: T[];
  nextCursor: string | null;
}

export interface PageParams {
  cursor?: string;
  limit?: number;
}

/* ---------- /me ---------- */
export interface Me {
  id: string;
  displayName: string | null;
  locale: Locale;
  timezone: string;
  voicePref: string | null;
  dailyBudgetUsd: number;
  isDemo: boolean;
}
export type MeUpdate = Partial<
  Pick<Me, "displayName" | "locale" | "timezone" | "voicePref" | "dailyBudgetUsd">
>;

/* ---------- /assistant/turns (SSE) ---------- */
export interface AssistantTurnRequest {
  conversationId?: string;
  text: string;
  locale: Locale;
  inputMode: InputMode;
}

/** Counts per PII entity type, e.g. {phone: 1, aadhaar: 0}. Never raw values. */
export type EntityCounts = Record<string, number>;

export interface TurnUsage {
  model?: string;
  tokensIn?: number;
  tokensOut?: number;
  costUsd?: number;
  escalated?: boolean;
}

export type TurnEvent =
  | { type: "meta"; conversationId: string; model: string }
  | { type: "privacy"; entityCounts: EntityCounts }
  | { type: "token"; delta: string }
  | { type: "tool"; skill: string; status: string }
  | { type: "pending_action"; id: string; summary: string }
  | { type: "done"; usage?: TurnUsage }
  | { type: "error"; code: string; message: string; requestId?: string };

export type TurnEventType = TurnEvent["type"];

/* ---------- conversations ---------- */
export interface Conversation {
  id: string;
  title: string | null;
  lastMessageAt: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  model?: string | null;
  createdAt: string;
}

/* ---------- memories ---------- */
export type MemoryKind = "fact" | "preference" | "person" | "note";

export interface Memory {
  id: string;
  kind: MemoryKind;
  content: string;
  source?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface MemoryInput {
  kind: MemoryKind;
  content: string;
}

/* ---------- pending actions ---------- */
export type PendingActionStatus =
  "pending" | "approved" | "rejected" | "expired" | "executed" | "failed";

export interface PendingAction {
  id: string;
  skill: string;
  actionType: string;
  summary: string;
  status: PendingActionStatus;
  createdAt: string;
  expiresAt?: string | null;
  decidedAt?: string | null;
}

/* ---------- privacy ---------- */
export interface PrivacyEvent {
  id: string;
  messageId?: string | null;
  entityCounts: EntityCounts;
  createdAt: string;
}

export interface PrivacyPreview {
  maskedText: string;
  entityCounts: EntityCounts;
}

/* ---------- budget ---------- */
export interface BudgetModelUsage {
  model: string;
  spendUsd: number;
  tokensIn: number;
  tokensOut: number;
}

export interface BudgetUsage {
  range: "day" | "week";
  spendUsd: number;
  capUsd: number;
  byModel: BudgetModelUsage[];
}
