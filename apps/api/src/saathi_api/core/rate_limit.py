"""In-process fixed-window rate limiter (single Render instance, 1 worker).

TODO(scale): move to Postgres/Redis if we ever run >1 instance.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from saathi_api.core.errors import RateLimited
from saathi_api.core.security import AuthUser, get_current_user


class RateLimiter:
    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, max_keys: int = 50_000
    ) -> None:
        self._clock = clock
        self._windows: dict[str, tuple[int, int]] = {}
        self._max_keys = max_keys

    def hit(self, key: str, limit: int, window_s: int = 60) -> None:
        now = self._clock()
        window = int(now // window_s)
        current_window, count = self._windows.get(key, (window, 0))
        if current_window != window:
            count = 0
        count += 1
        if len(self._windows) >= self._max_keys and key not in self._windows:
            self._windows.clear()  # crude memory bound; windows are only 60 s anyway
        self._windows[key] = (window, count)
        if count > limit:
            retry_after = int((window + 1) * window_s - now) + 1
            raise RateLimited(retry_after_s=retry_after)

    def reset(self) -> None:
        self._windows.clear()


def _limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.services.rate_limiter
    return limiter


async def limit_default(
    request: Request, user: Annotated[AuthUser, Depends(get_current_user)]
) -> None:
    limit = request.app.state.services.settings.rate_limit_default_per_min
    _limiter(request).hit(f"default:{user.id}", limit)


async def limit_turns(
    request: Request, user: Annotated[AuthUser, Depends(get_current_user)]
) -> None:
    limit = request.app.state.services.settings.rate_limit_turns_per_min
    _limiter(request).hit(f"turns:{user.id}", limit)
