"""Retry with exponential backoff + jitter, and a small async circuit breaker."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    """Opens after `failure_threshold` consecutive failures; one trial call after `reset_s`."""

    def __init__(
        self,
        failure_threshold: int,
        reset_s: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_s = reset_s
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._trial_in_flight = False

    @property
    def state(self) -> CircuitState:
        if self._opened_at is None:
            return CircuitState.CLOSED
        if self._clock() - self._opened_at >= self.reset_s:
            return CircuitState.HALF_OPEN
        return CircuitState.OPEN

    def before_call(self) -> None:
        state = self.state
        if state is CircuitState.OPEN:
            raise CircuitOpenError
        if state is CircuitState.HALF_OPEN:
            if self._trial_in_flight:
                raise CircuitOpenError
            self._trial_in_flight = True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._trial_in_flight = False

    def record_failure(self) -> None:
        self._trial_in_flight = False
        self._failures += 1
        if self._failures >= self.failure_threshold or self._opened_at is not None:
            self._opened_at = self._clock()


async def retry_async[T](
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay_s: float,
    is_retryable: Callable[[BaseException], bool],
    max_delay_s: float = 4.0,
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            if attempt >= attempts or not is_retryable(exc):
                raise
            delay = min(max_delay_s, base_delay_s * 2 ** (attempt - 1))
            await asyncio.sleep(delay + random.uniform(0, delay / 2))  # noqa: S311 - jitter only
    raise AssertionError("unreachable")  # pragma: no cover
