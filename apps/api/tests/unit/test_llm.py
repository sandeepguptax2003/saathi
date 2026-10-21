from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence

import httpx
import pytest

from saathi_api.core.errors import LLMUnavailable, UpstreamError
from saathi_api.core.resilience import CircuitBreaker, CircuitState
from saathi_api.modules.llm.schemas import (
    ChatMessage,
    LLMResult,
    RawCompletion,
    RawDelta,
    StreamUsage,
)
from saathi_api.modules.llm.service import LLMClient, LLMService
from tests.conftest import make_settings


class ScriptedBackend:
    """complete(): pops scripted results per model; Exceptions are raised."""

    def __init__(self, script: dict[str, list[object]]) -> None:
        self.script = script
        self.calls: list[str] = []

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> RawCompletion:
        self.calls.append(model)
        item = self.script[model].pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, str)
        return RawCompletion(item, 10, 5)

    async def stream(
        self, *, model: str, messages: Sequence[ChatMessage], max_tokens: int, temperature: float
    ) -> AsyncIterator[RawDelta]:
        self.calls.append(model)
        item = self.script[model].pop(0)
        if isinstance(item, Exception):
            raise item
        for w in str(item).split(" "):
            yield RawDelta(delta=w + " ")
        yield RawDelta(tokens_in=7, tokens_out=3)

    async def embed(
        self, *, model: str, texts: Sequence[str], dims: int
    ) -> tuple[list[list[float]], int]:
        return [[0.0] * dims for _ in texts], 1

    async def ping(self) -> bool:
        return True


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    async def record(self, **kw: object) -> None:
        self.rows.append(kw)


def client(script: dict[str, list[object]], **kw: object) -> tuple[LLMClient, ScriptedBackend]:
    s = make_settings(**kw)
    backend = ScriptedBackend(script)
    return LLMClient(backend, s), backend


FAST = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
SUPER = "nvidia/nemotron-3-super-120b-a12b"


async def test_retries_transient_errors_then_succeeds() -> None:
    c, b = client({FAST: [httpx.ConnectTimeout("t"), httpx.ConnectError("c"), "ok"]})
    r = await c.complete([ChatMessage("user", "hi")], model=FAST)
    assert r.text == "ok" and b.calls == [FAST] * 3


async def test_non_retryable_fails_fast() -> None:
    c, b = client({FAST: [ValueError("bad"), "never"]})
    with pytest.raises(UpstreamError):
        await c.complete([ChatMessage("user", "hi")], model=FAST)
    assert b.calls == [FAST]


async def test_circuit_opens_then_503() -> None:
    c, _ = client({FAST: [ValueError("x")] * 5}, circuit_failure_threshold=2)
    for _ in range(2):
        with pytest.raises(UpstreamError):
            await c.complete([ChatMessage("user", "hi")], model=FAST)
    with pytest.raises(LLMUnavailable):
        await c.complete([ChatMessage("user", "hi")], model=FAST)


def test_breaker_half_open_trial() -> None:
    t = [0.0]
    br = CircuitBreaker(1, 10, clock=lambda: t[0])
    br.record_failure()
    assert br.state is CircuitState.OPEN
    t[0] = 11
    assert br.state is CircuitState.HALF_OPEN
    br.before_call()
    br.record_success()
    assert br.state is CircuitState.CLOSED


async def test_router_escalates_low_confidence_to_super_and_records_cost() -> None:
    low = json.dumps({"intent": "skill", "skill": "bills", "confidence": 0.3})
    high = json.dumps(
        {"intent": "skill", "skill": "bills", "args": {"action": "pay"}, "confidence": 0.95}
    )
    c, b = client({FAST: [low], SUPER: [high]})
    rec = Recorder()
    d = await LLMService(c, rec, user_id=None).route("bill bhar do", "- bills")
    assert d.skill == "bills" and d.escalated and d.model == SUPER
    assert b.calls == [FAST, SUPER]
    assert [r["escalated"] for r in rec.rows] == [False, True]


async def test_router_keeps_nano_when_confident() -> None:
    c, b = client({FAST: ['Sure: {"intent": "chat", "confidence": 0.9}']})
    d = await LLMService(c, None, user_id=None).route("hello", "")
    assert d.intent == "chat" and not d.escalated and b.calls == [FAST]


async def test_super_failure_falls_back_to_nano_answer() -> None:
    c, _ = client({FAST: ["not json"], SUPER: [ValueError("down")]})
    svc = LLMService(c, None, user_id=None)

    def never_ok(_: LLMResult) -> bool:
        return False

    r = await svc.complete_with_escalation([ChatMessage("user", "x")], quality_ok=never_ok)
    assert r.model == FAST and r.text == "not json"


async def test_stream_falls_back_super_to_nano_and_records_usage() -> None:
    c, b = client({SUPER: [ValueError("down")], FAST: ["namaste ji"]})
    rec = Recorder()
    usage = StreamUsage(model="")
    out = [
        d
        async for d in LLMService(c, rec, user_id=None).stream(
            [ChatMessage("user", "x")], tier="reasoning", usage=usage
        )
    ]
    assert "".join(out).strip() == "namaste ji"
    assert usage.model == FAST and usage.tokens_in == 7 and usage.tokens_out == 3
    assert rec.rows[-1]["model"] == FAST
