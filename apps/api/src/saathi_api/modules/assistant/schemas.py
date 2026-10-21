from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import orjson
from pydantic import Field

from saathi_api.core.schemas import CamelModel

InputMode = Literal["voice", "text"]
SseEventName = Literal["meta", "privacy", "token", "tool", "pending_action", "done", "error"]


class TurnIn(CamelModel):
    conversation_id: uuid.UUID | None = None
    text: str = Field(min_length=1, max_length=2000)
    locale: Literal["hi-IN", "en-IN"] = "hi-IN"
    input_mode: InputMode = "text"


class ConversationOut(CamelModel):
    id: uuid.UUID
    title: str | None
    last_message_at: datetime
    created_at: datetime


class MessageOut(CamelModel):
    id: uuid.UUID
    role: str
    content_masked: str
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    created_at: datetime


class ConversationDeletedOut(CamelModel):
    id: uuid.UUID
    deleted: bool = True


@dataclass(frozen=True, slots=True)
class SseEvent:
    event: SseEventName
    data: dict[str, Any]

    def encode(self) -> bytes:
        return b"event: " + self.event.encode() + b"\ndata: " + orjson.dumps(self.data) + b"\n\n"


class TurnUsageOut(CamelModel):
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    escalated: bool
    first_token_ms: int | None
    latency_ms: int
