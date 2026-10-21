"""Model backends (external data access): real OpenAI-compatible Token Factory + a mock."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, cast

import httpx
from openai import AsyncOpenAI, omit
from openai.types.chat import ChatCompletionMessageParam

from saathi_api.core.config import Settings
from saathi_api.modules.llm.schemas import ChatMessage, RawCompletion, RawDelta


class ChatBackend(Protocol):
    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> RawCompletion: ...

    def stream(
        self, *, model: str, messages: Sequence[ChatMessage], max_tokens: int, temperature: float
    ) -> AsyncIterator[RawDelta]: ...

    async def embed(
        self, *, model: str, texts: Sequence[str], dims: int
    ) -> tuple[list[list[float]], int]: ...

    async def ping(self) -> bool: ...


def _to_openai(messages: Sequence[ChatMessage]) -> list[ChatCompletionMessageParam]:
    return [cast(ChatCompletionMessageParam, m.as_openai()) for m in messages]


class OpenAICompatibleBackend:
    """Nebius Token Factory via the OpenAI SDK. SDK retries are off; LLMClient owns retries."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        if settings.nebius_api_key is None:
            raise ValueError("NEBIUS_API_KEY is required for the Token Factory backend")
        self._client = AsyncOpenAI(
            base_url=settings.nebius_base_url,
            api_key=settings.nebius_api_key.get_secret_value(),
            max_retries=0,
            timeout=settings.llm_timeout_s,
        )
        # The OpenAI SDK pools its own connections (its transport is not our httpx client);
        # `http_client` is kept in the signature for probes that need plain HTTP.
        self._http = http_client

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> RawCompletion:
        resp = await self._client.chat.completions.create(
            model=model,
            messages=_to_openai(messages),
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            response_format={"type": "json_object"} if json_mode else omit,
        )
        text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        usage = resp.usage
        return RawCompletion(
            text=text,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
        )

    async def stream(
        self, *, model: str, messages: Sequence[ChatMessage], max_tokens: int, temperature: float
    ) -> AsyncIterator[RawDelta]:
        resp = await self._client.chat.completions.create(
            model=model,
            messages=_to_openai(messages),
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield RawDelta(delta=chunk.choices[0].delta.content)
            if chunk.usage:
                yield RawDelta(
                    tokens_in=chunk.usage.prompt_tokens, tokens_out=chunk.usage.completion_tokens
                )

    async def embed(
        self, *, model: str, texts: Sequence[str], dims: int
    ) -> tuple[list[list[float]], int]:
        resp = await self._client.embeddings.create(model=model, input=list(texts), dimensions=dims)
        vectors = [list(d.embedding)[:dims] for d in resp.data]
        return vectors, resp.usage.prompt_tokens if resp.usage else 0

    async def ping(self) -> bool:
        await self._client.models.list()
        return True


# --------------------------------------------------------------------------- mock
_SKILL_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("daily-brief", ("brief", "aaj ka plan", "today's plan", "summary of my day", "din kaisa")),
    ("bills", ("bill", "bijli", "electricity", "recharge", "pay ", "bhugtan")),
    ("email-triage", ("email", "inbox", "mail")),
    ("calendar", ("calendar", "meeting", "schedule", "event")),
    ("reminders", ("remind", "yaad", "reminder")),
)


def mock_route(text: str) -> dict[str, Any]:
    lowered = text.lower()
    for skill, words in _SKILL_KEYWORDS:
        if any(w in lowered for w in words):
            args: dict[str, Any] = {}
            if skill == "bills" and re.search(r"\b(pay|bhar|bhugtan)", lowered):
                args = {"action": "pay"}
            if skill == "reminders":
                args = {"action": "create", "text": text[:200]}
            return {"intent": "skill", "skill": skill, "args": args, "confidence": 0.9}
    return {"intent": "chat", "skill": None, "args": {}, "confidence": 0.8}


class MockBackend:
    """Deterministic, offline backend for tests, CI and demo without credits (LLM_MOCK=true)."""

    def __init__(self, *, delay_s: float = 0.0, reply: str | None = None) -> None:
        self.delay_s = delay_s
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def _approx_tokens(text: str) -> int:
        return max(1, math.ceil(len(text) / 4))

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> RawCompletion:
        self.calls.append(("complete", model))
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        text = json.dumps(mock_route(last_user)) if json_mode else self._reply_for(last_user)
        prompt = " ".join(m.content for m in messages)
        return RawCompletion(text, self._approx_tokens(prompt), self._approx_tokens(text))

    def _reply_for(self, user_text: str) -> str:
        if self.reply is not None:
            return self.reply
        return f"Theek hai! Maine samjha: {user_text[:120]}. Aur kuch madad chahiye?"

    async def stream(
        self, *, model: str, messages: Sequence[ChatMessage], max_tokens: int, temperature: float
    ) -> AsyncIterator[RawDelta]:
        self.calls.append(("stream", model))
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        text = self._reply_for(last_user)
        for word in re.findall(r"\S+\s*", text):
            if self.delay_s:
                await asyncio.sleep(self.delay_s)
            yield RawDelta(delta=word)
        prompt = " ".join(m.content for m in messages)
        yield RawDelta(tokens_in=self._approx_tokens(prompt), tokens_out=self._approx_tokens(text))

    async def embed(
        self, *, model: str, texts: Sequence[str], dims: int
    ) -> tuple[list[list[float]], int]:
        self.calls.append(("embed", model))
        return [hash_embedding(t, dims) for t in texts], sum(self._approx_tokens(t) for t in texts)

    async def ping(self) -> bool:
        return True


def hash_embedding(text: str, dims: int) -> list[float]:
    """Cheap deterministic bag-of-words embedding (unit length) for mock mode."""
    vec = [0.0] * dims
    for word in re.findall(r"\w+", text.lower()):
        h = int.from_bytes(hashlib.blake2b(word.encode(), digest_size=8).digest(), "big")
        vec[h % dims] += 1.0 if (h >> 63) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
