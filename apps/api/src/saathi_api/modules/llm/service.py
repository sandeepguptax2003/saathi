"""LLM client (timeouts, retries, circuit breaker), cost recording, routing and escalation.

- LLMClient: process singleton around a ChatBackend. Owns retries + breaker.
- LLMService: per-request facade that records every call's usage through a UsageRecorder.
- Escalation: Nano first; Super on low confidence / invalid JSON / Nano failure. Super failure
  falls back to the Nano result (or Nano itself for streams).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Protocol

import httpx
import openai
from pydantic import ValidationError

from saathi_api.core.config import Settings
from saathi_api.core.context import current_request_id
from saathi_api.core.errors import LLMUnavailable, UpstreamError
from saathi_api.core.logging import get_logger
from saathi_api.core.resilience import CircuitBreaker, CircuitOpenError, retry_async
from saathi_api.modules.llm.repository import ChatBackend
from saathi_api.modules.llm.schemas import (
    ChatMessage,
    LLMResult,
    RawCompletion,
    RawDelta,
    RouteDecision,
    StreamUsage,
    Tier,
)

log = get_logger(__name__)


class UsageRecorder(Protocol):
    async def record(
        self,
        *,
        user_id: uuid.UUID | None,
        model: str,
        tokens_in: int,
        tokens_out: int,
        escalated: bool,
        request_id: str | None,
    ) -> object: ...


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError | httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, openai.APITimeoutError | openai.APIConnectionError | openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code >= 500
    return False


class LLMClient:
    def __init__(self, backend: ChatBackend, settings: Settings) -> None:
        self.backend = backend
        self.settings = settings
        self.breaker = CircuitBreaker(settings.circuit_failure_threshold, settings.circuit_reset_s)

    def model_for(self, tier: Tier) -> str:
        return self.settings.model_fast if tier == "fast" else self.settings.model_reasoning

    async def _guarded[T](self, fn: Callable[[], Awaitable[T]]) -> T:
        try:
            self.breaker.before_call()
        except CircuitOpenError as exc:
            raise LLMUnavailable(details={"circuit": "open"}) from exc

        async def attempt() -> T:
            async with asyncio.timeout(self.settings.llm_timeout_s):
                return await fn()

        try:
            result = await retry_async(
                attempt,
                attempts=self.settings.llm_max_retries,
                base_delay_s=self.settings.llm_retry_base_delay_s,
                is_retryable=is_retryable,
            )
        except Exception as exc:
            self.breaker.record_failure()
            log.warning(
                "llm_call_failed", error=type(exc).__name__, circuit=self.breaker.state.value
            )
            raise UpstreamError(
                "AI model call failed", details={"reason": type(exc).__name__}
            ) from exc
        self.breaker.record_success()
        return result

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> LLMResult:
        started = time.perf_counter()
        raw: RawCompletion = await self._guarded(
            lambda: self.backend.complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                temperature=temperature,
                json_mode=json_mode,
            )
        )
        return LLMResult(
            text=raw.text,
            model=model,
            tokens_in=raw.tokens_in,
            tokens_out=raw.tokens_out,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def open_stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str,
        max_tokens: int | None = None,
        temperature: float = 0.5,
    ) -> tuple[RawDelta, AsyncIterator[RawDelta]]:
        """Retry until the first chunk arrives (first-token timeout), then hand over the stream."""

        async def first() -> tuple[RawDelta, AsyncIterator[RawDelta]]:
            it = aiter(
                self.backend.stream(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens or self.settings.llm_max_tokens,
                    temperature=temperature,
                )
            )
            head = await anext(it)
            return head, it

        return await self._guarded(first)

    async def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        return await self._guarded(
            lambda: self.backend.embed(
                model=self.settings.model_embed, texts=texts, dims=self.settings.embed_dims
            )
        )

    async def ping(self) -> bool:
        try:
            async with asyncio.timeout(5):
                return await self.backend.ping()
        except Exception:
            return False


ROUTER_SYSTEM_PROMPT = """You are Saathi's intent router. Output ONLY a JSON object:
{"intent": "chat"|"skill", "skill": string|null, "args": object, "confidence": 0..1,
 "needs_reasoning": boolean}
Available skills:
{skills}
Text may contain placeholders like <PHONE_1>; copy them verbatim into args. Never invent values."""


class LLMService:
    def __init__(
        self,
        client: LLMClient,
        recorder: UsageRecorder | None,
        *,
        user_id: uuid.UUID | None,
    ) -> None:
        self.client = client
        self.recorder = recorder
        self.user_id = user_id
        self.settings = client.settings

    async def _record(self, model: str, tokens_in: int, tokens_out: int, escalated: bool) -> None:
        if self.recorder is not None:
            await self.recorder.record(
                user_id=self.user_id,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                escalated=escalated,
                request_id=current_request_id(),
            )

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tier: Tier = "fast",
        json_mode: bool = False,
        max_tokens: int | None = None,
        escalated: bool = False,
    ) -> LLMResult:
        result = await self.client.complete(
            messages, model=self.client.model_for(tier), json_mode=json_mode, max_tokens=max_tokens
        )
        await self._record(result.model, result.tokens_in, result.tokens_out, escalated)
        return result

    async def complete_with_escalation(
        self,
        messages: Sequence[ChatMessage],
        *,
        quality_ok: Callable[[LLMResult], bool],
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> LLMResult:
        fast: LLMResult | None = None
        try:
            fast = await self.complete(
                messages, tier="fast", json_mode=json_mode, max_tokens=max_tokens
            )
            if quality_ok(fast):
                return fast
            log.info("llm_escalate", reason="quality")
        except UpstreamError:
            log.info("llm_escalate", reason="fast_failed")
        try:
            strong = await self.complete(
                messages,
                tier="reasoning",
                json_mode=json_mode,
                max_tokens=max_tokens,
                escalated=True,
            )
        except (UpstreamError, LLMUnavailable):
            if fast is not None:
                return fast
            raise
        return LLMResult(
            text=strong.text,
            model=strong.model,
            tokens_in=strong.tokens_in,
            tokens_out=strong.tokens_out,
            latency_ms=strong.latency_ms,
            escalated=True,
        )

    async def route(self, masked_text: str, skills_catalog: str) -> RouteDecision:
        messages = [
            ChatMessage("system", ROUTER_SYSTEM_PROMPT.replace("{skills}", skills_catalog)),
            ChatMessage("user", masked_text),
        ]
        threshold = self.settings.llm_router_confidence_min

        def parse(result: LLMResult) -> RouteDecision | None:
            try:
                data = json.loads(_extract_json(result.text))
                return RouteDecision.model_validate(data)
            except (ValueError, ValidationError):
                return None

        def good(result: LLMResult) -> bool:
            decision = parse(result)
            return decision is not None and decision.confidence >= threshold

        result = await self.complete_with_escalation(
            messages, quality_ok=good, json_mode=True, max_tokens=256
        )
        parsed = parse(result)
        decision = parsed or RouteDecision(intent="chat", confidence=0.0)
        log.info(
            "route_decision",
            intent=decision.intent,
            skill=decision.skill,
            confidence=decision.confidence,
            parsed=parsed is not None,
            model=result.model,
            tokens_out=result.tokens_out,
            chars=len(result.text),
        )
        decision.model = result.model
        decision.escalated = result.escalated
        return decision

    async def stream(
        self, messages: Sequence[ChatMessage], *, tier: Tier, usage: StreamUsage
    ) -> AsyncIterator[str]:
        """Yield text deltas. Falls back reasoning -> fast if the strong model fails to start."""
        started = time.perf_counter()
        model = self.client.model_for(tier)
        try:
            head, rest = await self.client.open_stream(messages, model=model)
        except (UpstreamError, LLMUnavailable):
            if tier == "fast":
                raise
            log.info("llm_fallback", frm=model, to=self.settings.model_fast)
            model = self.settings.model_fast
            head, rest = await self.client.open_stream(messages, model=model)
        usage.model = model
        usage.escalated = usage.escalated or tier == "reasoning"
        usage.first_token_ms = int((time.perf_counter() - started) * 1000)
        produced: list[str] = []

        async def chunks() -> AsyncIterator[RawDelta]:
            yield head
            async for d in rest:
                yield d

        try:
            async for d in chunks():
                if d.delta:
                    produced.append(d.delta)
                    yield d.delta
                if d.tokens_in is not None:
                    usage.tokens_in = d.tokens_in
                if d.tokens_out is not None:
                    usage.tokens_out = d.tokens_out
        finally:
            if usage.tokens_out == 0 and produced:  # provider sent no usage chunk: estimate
                usage.tokens_out = max(1, len("".join(produced)) // 4)
                usage.tokens_in = usage.tokens_in or sum(len(m.content) for m in messages) // 4
            usage.latency_ms = int((time.perf_counter() - started) * 1000)
            await self._record(usage.model, usage.tokens_in, usage.tokens_out, usage.escalated)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors, tokens = await self.client.embed(texts)
        await self._record(self.settings.model_embed, tokens, 0, False)
        return vectors


def _extract_json(text: str) -> str:
    """Nano may wrap JSON in prose or code fences; take the outermost object."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no json object")
    return text[start : end + 1]
