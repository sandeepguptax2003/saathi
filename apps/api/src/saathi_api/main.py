"""App factory: settings -> logging/Sentry -> singletons -> middleware -> routers -> handlers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from saathi_api import __version__
from saathi_api.core.config import Settings, get_settings
from saathi_api.core.crypto import Encryptor
from saathi_api.core.db import Database
from saathi_api.core.errors import install_error_handlers
from saathi_api.core.health import router as health_router
from saathi_api.core.http_client import build_http_client
from saathi_api.core.logging import configure_logging, get_logger
from saathi_api.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from saathi_api.core.rate_limit import RateLimiter
from saathi_api.deps import Services
from saathi_api.modules.approvals.router import router as approvals_router
from saathi_api.modules.assistant.router import router as assistant_router
from saathi_api.modules.budget.router import router as budget_router
from saathi_api.modules.llm.repository import ChatBackend, MockBackend, OpenAICompatibleBackend
from saathi_api.modules.llm.router import router as llm_router
from saathi_api.modules.llm.service import LLMClient
from saathi_api.modules.memory.router import router as memory_router
from saathi_api.modules.privacy.router import router as privacy_router
from saathi_api.modules.skills.router import router as skills_router
from saathi_api.modules.users.router import router as users_router
from saathi_api.modules.voice.router import router as voice_router

API_PREFIX = "/api/v1"
log = get_logger(__name__)


def _init_sentry(settings: Settings) -> None:
    if settings.sentry_dsn is None:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.env,
        release=settings.release or __version__,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )


def build_services(settings: Settings, *, backend: ChatBackend | None = None) -> Services:
    http = build_http_client(settings)
    if backend is None:
        backend = MockBackend() if settings.llm_mock else OpenAICompatibleBackend(settings, http)
    return Services(
        settings=settings,
        db=Database(settings),
        http=http,
        llm=LLMClient(backend, settings),
        encryptor=Encryptor(settings.peppers(), settings.encryption_key_version),
        rate_limiter=RateLimiter(),
    )


def create_app(settings: Settings | None = None, *, services: Services | None = None) -> FastAPI:
    settings = settings or (services.settings if services else get_settings())
    configure_logging(settings.log_level, json=settings.env != "local")
    _init_sentry(settings)
    services = services or build_services(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        log.info("startup", env=settings.env, version=__version__, llm_mock=settings.llm_mock)
        yield
        await services.http.aclose()
        await services.db.dispose()
        log.info("shutdown")

    docs = not settings.is_production
    app = FastAPI(
        title="Saathi API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.state.services = services

    # Middleware: last added = outermost. Order (outer -> inner):
    # RequestContext -> SecurityHeaders -> CORS -> GZip -> app
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After", "Idempotent-Replayed"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(RequestContextMiddleware)

    install_error_handlers(app)

    app.include_router(health_router)  # /health, /ready at root for probes + keep-alive
    app.include_router(health_router, prefix=API_PREFIX, include_in_schema=False)
    api = APIRouter(prefix=API_PREFIX)
    for r in (
        users_router,
        assistant_router,
        memory_router,
        approvals_router,
        privacy_router,
        budget_router,
        skills_router,
        llm_router,
        voice_router,
    ):
        api.include_router(r)
    app.include_router(api)
    return app


def __getattr__(name: str) -> FastAPI:
    """`uvicorn saathi_api.main:app` builds the app lazily so importing this module (tests,
    tooling) never requires production env vars."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
