"""Request-scoped context (request id, user id) shared by logs, errors and envelopes."""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def current_request_id() -> str:
    return request_id_var.get()
