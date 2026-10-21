"""Error taxonomy and the {error:{code,message,requestId,details}} envelope handlers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from saathi_api.core.context import current_request_id
from saathi_api.core.logging import get_logger

log = get_logger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Something went wrong"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        self.headers = headers or {}
        if code is not None:
            self.code = code
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code, code, message = 400, "validation_error", "Request validation failed"


class Unauthorized(AppError):
    status_code, code, message = 401, "unauthorized", "Missing or invalid credentials"


class Forbidden(AppError):
    status_code, code, message = 403, "forbidden", "Not allowed"


class NotFound(AppError):
    status_code, code, message = 404, "not_found", "Resource not found"


class Conflict(AppError):
    status_code, code, message = 409, "conflict", "Conflicting state"


class Unprocessable(AppError):
    status_code, code, message = 422, "unprocessable", "Request could not be processed"


class _RetryAfterError(AppError):
    status_code = 429

    def __init__(self, message: str | None = None, *, retry_after_s: int, **kw: Any) -> None:
        super().__init__(message, **kw)
        self.retry_after_s = max(1, int(retry_after_s))
        self.headers["Retry-After"] = str(self.retry_after_s)
        self.details.setdefault("retryAfterSeconds", self.retry_after_s)


class RateLimited(_RetryAfterError):
    code, message = "rate_limited", "Too many requests"


class BudgetExceeded(_RetryAfterError):
    code, message = "budget_exceeded", "Daily AI budget reached"


class UpstreamError(AppError):
    status_code, code, message = 502, "upstream_error", "Upstream service failed"


class LLMUnavailable(AppError):
    status_code, code, message = 503, "llm_unavailable", "AI model temporarily unavailable"


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "requestId": current_request_id(),
            "details": details or {},
        }
    }


def error_response(
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(error_body(code, message, details), status_code=status, headers=headers)


_HTTP_CODES = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "unprocessable",
    429: "rate_limited",
}


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # pragma: no cover - registration guarantees type
        raise exc
    if exc.status_code >= 500:
        log.warning("app_error", code=exc.code, status=exc.status_code)
    return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


def validation_issues(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """JSON-safe subset of pydantic error dicts (ctx may hold exception objects)."""
    return [
        {
            "loc": [str(p) for p in e.get("loc", ())],
            "msg": str(e.get("msg", "")),
            "type": e.get("type"),
        }
        for e in errors
    ]


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover
        raise exc
    issues = validation_issues(exc.errors())
    return error_response(400, "validation_error", "Request validation failed", {"issues": issues})


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover
        raise exc
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return error_response(exc.status_code, code, message, headers=dict(exc.headers or {}))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    # Unhandled exceptions are converted to the envelope in RequestContextMiddleware so the
    # response still carries X-Request-ID and is never a bare HTML 500.
