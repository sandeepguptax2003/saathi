"""Pure-ASGI middleware: request id + access log + last-resort error envelope; security headers."""

from __future__ import annotations

import re
import time
import uuid

import orjson
import sentry_sdk
import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from saathi_api.core.context import request_id_var
from saathi_api.core.errors import error_body
from saathi_api.core.logging import get_logger

log = get_logger("saathi.access")
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = next(
            (v.decode("latin-1") for k, v in scope["headers"] if k == b"x-request-id"), ""
        )
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        request_id_var.set(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            log.exception("unhandled_error", path=scope.get("path"))
            if response_started:
                raise
            body = orjson.dumps(error_body("internal_error", "Something went wrong"))
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"x-request-id", request_id.encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            status = 500
        finally:
            path = scope.get("path", "")
            if path not in {"/health", "/api/v1/health"}:
                log.info(
                    "request",
                    method=scope.get("method"),
                    path=path,
                    status=status,
                    latency_ms=round((time.perf_counter() - started) * 1000, 1),
                )


_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = str(scope.get("path", "")).startswith(_DOCS_PATHS)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                h = MutableHeaders(scope=message)
                h.setdefault("X-Content-Type-Options", "nosniff")
                h.setdefault("X-Frame-Options", "DENY")
                h.setdefault("Referrer-Policy", "no-referrer")
                h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
                h.setdefault("Cross-Origin-Resource-Policy", "same-site")
                h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if not is_docs:
                    h.setdefault(
                        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
                    )
                    h.setdefault("Cache-Control", "no-store")
                if self.hsts:
                    h.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
            await send(message)

        await self.app(scope, receive, send_wrapper)
