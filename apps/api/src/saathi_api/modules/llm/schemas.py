from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]
Tier = Literal["fast", "reasoning"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str

    def as_openai(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class RawCompletion:
    text: str
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True, slots=True)
class RawDelta:
    delta: str = ""
    tokens_in: int | None = None
    tokens_out: int | None = None


@dataclass(frozen=True, slots=True)
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    escalated: bool = False


@dataclass(slots=True)
class StreamUsage:
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    first_token_ms: int | None = None
    escalated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class RouteDecision(BaseModel):
    """Router output (JSON from Nano). `skill` None means plain chat."""

    intent: Literal["chat", "skill"] = "chat"
    skill: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    needs_reasoning: bool = False
    model: str = ""
    escalated: bool = False
