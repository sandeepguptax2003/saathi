"""GET /health (liveness, best-effort DB touch for keep-alive) and GET /ready (DB + LLM)."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from saathi_api import __version__
from saathi_api.core.logging import get_logger
from saathi_api.core.schemas import CamelModel, Envelope, ok

log = get_logger(__name__)
router = APIRouter(tags=["health"])

CheckStatus = Literal["ok", "down", "skipped"]


class HealthOut(CamelModel):
    status: Literal["ok"]
    version: str
    env: str
    db: CheckStatus


class ReadyOut(CamelModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, CheckStatus]


async def _db_ok(request: Request, timeout_s: float) -> bool:
    try:
        async with asyncio.timeout(timeout_s):
            return bool(await request.app.state.services.db.ping())
    except Exception as exc:
        log.warning("db_ping_failed", error=type(exc).__name__)
        return False


@router.get("/health")
async def health(request: Request) -> Envelope[HealthOut]:
    """Always 200 while the process is alive. Touches the DB so keep-alive pings also keep
    Supabase awake; DB state is reported, not enforced (that is /ready's job)."""
    services = request.app.state.services
    db_status: CheckStatus = "ok" if await _db_ok(request, 2.0) else "down"
    return ok(HealthOut(status="ok", version=__version__, env=services.settings.env, db=db_status))


@router.get("/ready", responses={503: {"model": Envelope[ReadyOut]}})
async def ready(request: Request) -> JSONResponse:
    services = request.app.state.services
    db_ok, llm_ok = await asyncio.gather(_db_ok(request, 3.0), services.llm.ping())
    checks: dict[str, CheckStatus] = {
        "db": "ok" if db_ok else "down",
        "llm": "ok" if llm_ok else "down",
    }
    if services.llm.breaker.state.value == "open":
        checks["llm"] = "down"
    is_ready = all(v == "ok" for v in checks.values())
    body = ok(ReadyOut(status="ready" if is_ready else "not_ready", checks=checks))
    return JSONResponse(
        body.model_dump(by_alias=True, mode="json"), status_code=200 if is_ready else 503
    )
